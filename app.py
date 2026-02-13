import os
import logging
import requests
import re
import hashlib
import json
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv
import threading
import time

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

#============================================
# Configuration
#============================================

PANEL_URL = "http://198.135.52.238"
PANEL_USERNAME = "selva"
PANEL_PASSWORD = "selva123456"

all_messages = []
MAX_MESSAGES = 100
debug_logs = []

bot_stats = {
    'start_time': datetime.now(),
    'total_otps': 0,
    'last_check': 'Never',
    'is_running': False,
    'scraper_status': 'Not initialized',
    'last_error': None,
    'api_response': None
}

scraper = None

#============================================
# أعلام الدول
#============================================

COUNTRY_FLAGS = {
    'venezuela': '🇻🇪', 've': '🇻🇪',
    'brazil': '🇧🇷', 'br': '🇧🇷',
    'argentina': '🇦🇷', 'ar': '🇦🇷',
    'colombia': '🇨🇴', 'co': '🇨🇴',
    'usa': '🇺🇸', 'us': '🇺🇸', 'united states': '🇺🇸',
    'canada': '🇨🇦', 'ca': '🇨🇦',
    'mexico': '🇲🇽', 'mx': '🇲🇽',
    'uk': '🇬🇧', 'gb': '🇬🇧', 'united kingdom': '🇬🇧',
    'germany': '🇩🇪', 'de': '🇩🇪',
    'france': '🇫🇷', 'fr': '🇫🇷',
    'italy': '🇮🇹', 'it': '🇮🇹',
    'spain': '🇪🇸', 'es': '🇪🇸',
    'russia': '🇷🇺', 'ru': '🇷🇺',
    'india': '🇮🇳', 'in': '🇮🇳',
    'china': '🇨🇳', 'cn': '🇨🇳',
    'japan': '🇯🇵', 'jp': '🇯🇵',
    'korea': '🇰🇷', 'kr': '🇰🇷',
    'indonesia': '🇮🇩', 'id': '🇮🇩',
    'malaysia': '🇲🇾', 'my': '🇲🇾',
    'philippines': '🇵🇭', 'ph': '🇵🇭',
    'vietnam': '🇻🇳', 'vn': '🇻🇳',
    'thailand': '🇹🇭', 'th': '🇹🇭',
    'singapore': '🇸🇬', 'sg': '🇸🇬',
    'pakistan': '🇵🇰', 'pk': '🇵🇰',
    'bangladesh': '🇧🇩', 'bd': '🇧🇩',
    'tajikistan': '🇹🇯', 'tj': '🇹🇯',
    'uzbekistan': '🇺🇿', 'uz': '🇺🇿',
    'kazakhstan': '🇰🇿', 'kz': '🇰🇿',
    'ukraine': '🇺🇦', 'ua': '🇺🇦',
    'poland': '🇵🇱', 'pl': '🇵🇱',
    'turkey': '🇹🇷', 'tr': '🇹🇷',
    'saudi': '🇸🇦', 'sa': '🇸🇦',
    'uae': '🇦🇪', 'ae': '🇦🇪',
    'egypt': '🇪🇬', 'eg': '🇪🇬',
    'morocco': '🇲🇦', 'ma': '🇲🇦',
    'nigeria': '🇳🇬', 'ng': '🇳🇬',
    'australia': '🇦🇺', 'au': '🇦🇺',
}

#============================================
# Debug Log
#============================================

def add_debug(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log = f"[{timestamp}] {message}"
    debug_logs.insert(0, log)
    if len(debug_logs) > 50:
        debug_logs.pop()
    logger.info(message)

#============================================
# إخفاء جزء من الرقم
#============================================

def mask_phone_number(phone):
    if not phone or phone == 'Unknown':
        return 'Unknown'
    phone = str(phone).strip()
    if len(phone) <= 6:
        return phone[:2] + '•••' + phone[-1:]
    if phone.startswith('+'):
        return f"{phone[:5]}•••{phone[-4:]}"
    return f"{phone[:4]}•••{phone[-4:]}"

#============================================
# API Scraper
#============================================

class PanelAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()
        self.logged_in = False
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 Chrome/120.0.0.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    
    def login(self):
        try:
            add_debug(f"🔐 Attempting login to {self.base_url}")
            
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=15
            )
            
            add_debug(f"📥 Login response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                add_debug(f"📥 Login response: {str(data)[:200]}")
                
                if 'token' in data:
                    self.token = data['token']
                    self.logged_in = True
                    self.session.headers['Authorization'] = f'Bearer {self.token}'
                    bot_stats['scraper_status'] = '✅ Connected'
                    add_debug("✅ Login successful!")
                    return True
                else:
                    add_debug(f"❌ No token in response: {data}")
            else:
                add_debug(f"❌ Login failed: {response.text[:200]}")
            
            bot_stats['scraper_status'] = '❌ Login failed'
            return False
            
        except Exception as e:
            add_debug(f"❌ Login error: {str(e)}")
            bot_stats['scraper_status'] = f'❌ Error: {str(e)[:50]}'
            bot_stats['last_error'] = str(e)
            return False
    
    def fetch_messages(self):
        if not self.logged_in:
            add_debug("⚠️ Not logged in, attempting login...")
            if not self.login():
                return []
        
        try:
            url = f"{self.base_url}/api/sms?limit=100"
            add_debug(f"📥 Fetching from: {url}")
            
            response = self.session.get(url, timeout=15)
            add_debug(f"📥 Response status: {response.status_code}")
            
            if response.status_code == 401:
                add_debug("⚠️ Token expired, re-logging in...")
                self.logged_in = False
                if not self.login():
                    return []
                response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                add_debug(f"❌ Failed to fetch: {response.status_code}")
                add_debug(f"Response: {response.text[:300]}")
                return []
            
            # حفظ الـ response للـ debug
            raw_data = response.text
            bot_stats['api_response'] = raw_data[:1000]
            add_debug(f"📥 Raw response: {raw_data[:300]}")
            
            try:
                data = response.json()
            except:
                add_debug(f"❌ Invalid JSON response")
                return []
            
            # معرفة نوع الـ response
            add_debug(f"📥 Response type: {type(data)}")
            
            if isinstance(data, list):
                messages = data
                add_debug(f"📥 Response is a list with {len(messages)} items")
            elif isinstance(data, dict):
                add_debug(f"📥 Response keys: {list(data.keys())}")
                messages = data.get('sms', data.get('messages', data.get('data', [])))
                add_debug(f"📥 Extracted {len(messages)} messages")
            else:
                add_debug(f"❌ Unknown response type: {type(data)}")
                messages = []
            
            if messages and len(messages) > 0:
                add_debug(f"📨 First message sample: {json.dumps(messages[0], ensure_ascii=False)[:300]}")
            
            formatted = []
            for i, m in enumerate(messages):
                f = self._format_message(m)
                if f:
                    formatted.append(f)
                    if i == 0:
                        add_debug(f"✅ Formatted first message: {f.get('otp')} - {f.get('service')}")
            
            add_debug(f"📨 Total formatted: {len(formatted)}")
            return formatted
            
        except Exception as e:
            add_debug(f"❌ Fetch error: {str(e)}")
            bot_stats['last_error'] = str(e)
            return []
    
    def _format_message(self, msg):
        try:
            content = msg.get('content', msg.get('message', msg.get('text', '')))
            otp = self._extract_otp(content)
            
            phone = msg.get('Number') or msg.get('number') or msg.get('phone') or 'Unknown'
            country_name = msg.get('country') or msg.get('Country') or ''
            country_flag = self._get_country_flag(country_name)
            
            service = (
                msg.get('service') or 
                msg.get('Service') or
                msg.get('sender') or 
                self._detect_service(content)
            )
            
            timestamp = msg.get('created_at', msg.get('timestamp', ''))
            if timestamp:
                try:
                    dt = datetime.strptime(str(timestamp)[:19], '%Y-%m-%dT%H:%M:%S')
                    timestamp = dt.strftime('%Y-%m-%d %I:%M %p')
                except:
                    timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p')
            else:
                timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p')
            
            return {
                'otp': otp,
                'phone': phone,
                'phone_masked': mask_phone_number(phone),
                'service': service,
                'country': country_name,
                'country_flag': country_flag,
                'timestamp': timestamp,
                'raw_message': content[:200] if content else '',
                'id': msg.get('id', msg.get('_id', str(hash(str(msg)))))
            }
        except Exception as e:
            add_debug(f"❌ Format error: {str(e)}")
            return None
    
    def _extract_otp(self, content):
        if not content:
            return 'N/A'
        
        patterns = [
            r'(\d{3}[-\s]?\d{3})',
            r'(\d{4}[-\s]?\d{4})',
            r'(?:code|kode|otp)[:\s]*(\d{4,8})',
            r'(\d{6})',
            r'(\d{4,8})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.I)
            if match:
                return match.group(1).replace(' ', '-')
        return 'N/A'
    
    def _detect_service(self, content):
        if not content:
            return 'Unknown'
        
        services = {
            'whatsapp': 'WhatsApp', 'telegram': 'Telegram',
            'facebook': 'Facebook', 'instagram': 'Instagram',
            'twitter': 'Twitter', 'google': 'Google',
            'tiktok': 'TikTok', 'snapchat': 'Snapchat',
        }
        
        content_lower = content.lower()
        for key, name in services.items():
            if key in content_lower:
                return name
        return 'SMS Service'
    
    def _get_country_flag(self, country):
        if not country:
            return '🌍'
        country_lower = country.lower().strip()
        if country_lower in COUNTRY_FLAGS:
            return COUNTRY_FLAGS[country_lower]
        for key, flag in COUNTRY_FLAGS.items():
            if key in country_lower:
                return flag
        return '🌍'


def create_scraper():
    try:
        add_debug("🔧 Creating scraper...")
        api = PanelAPI(PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD)
        if api.login():
            add_debug("✅ Scraper ready")
        return api
    except Exception as e:
        add_debug(f"❌ Scraper error: {str(e)}")
        return None

#============================================
# OTP Filter
#============================================

class OTPFilter:
    def __init__(self):
        self.cache = set()
    
    def is_new(self, msg_id):
        if msg_id in self.cache:
            return False
        self.cache.add(msg_id)
        return True
    
    def clear(self):
        self.cache.clear()

otp_filter = OTPFilter()

#============================================
# Background Monitor
#============================================

def check_and_update():
    global scraper, all_messages
    
    try:
        add_debug("🔄 Starting check...")
        
        if not scraper:
            add_debug("⚠️ No scraper, creating...")
            scraper = create_scraper()
            if not scraper:
                add_debug("❌ Failed to create scraper")
                return
        
        if not scraper.logged_in:
            add_debug("⚠️ Not logged in, logging in...")
            if not scraper.login():
                add_debug("❌ Login failed")
                return
        
        messages = scraper.fetch_messages()
        bot_stats['last_check'] = datetime.now().strftime('%H:%M:%S')
        
        add_debug(f"📨 Fetched {len(messages)} messages")
        
        new_count = 0
        for msg in messages:
            if otp_filter.is_new(msg['id']):
                all_messages.insert(0, msg)
                bot_stats['total_otps'] += 1
                new_count += 1
        
        add_debug(f"🆕 New messages: {new_count}")
        
        all_messages = all_messages[:MAX_MESSAGES]
                
    except Exception as e:
        add_debug(f"❌ Check error: {str(e)}")
        bot_stats['last_error'] = str(e)

def background_monitor():
    bot_stats['is_running'] = True
    add_debug("🚀 Background monitor started")
    
    # First check immediately
    check_and_update()
    
    while bot_stats['is_running']:
        try:
            time.sleep(10)
            check_and_update()
        except Exception as e:
            add_debug(f"❌ Monitor error: {str(e)}")
            time.sleep(30)

#============================================
# HTML Template
#============================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📱 SMS OTP Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            color: #fff;
        }
        
        .header {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .logo { font-size: 24px; font-weight: 700; }
        
        .stats-bar { display: flex; gap: 20px; flex-wrap: wrap; }
        
        .stat-item {
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            border-radius: 10px;
        }
        
        .stat-value { font-size: 20px; font-weight: 700; color: #00ff88; }
        .stat-label { font-size: 12px; color: #aaa; }
        
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
        }
        
        .status-online { background: rgba(0,255,136,0.2); color: #00ff88; }
        .status-offline { background: rgba(255,68,68,0.2); color: #ff4444; }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        .btn {
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            margin: 5px;
        }
        
        .btn-primary { background: linear-gradient(135deg, #00ff88, #00cc6a); color: #000; }
        .btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
        .btn-danger { background: #ff4444; color: #fff; }
        
        .messages-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .message-card {
            background: rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            animation: fadeIn 0.5s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
        }
        
        .country-info { display: flex; align-items: center; gap: 10px; }
        .country-flag { font-size: 32px; }
        .country-name { font-weight: 600; }
        
        .service-badge {
            background: linear-gradient(135deg, #667eea, #764ba2);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
        }
        
        .otp-section {
            background: rgba(0,255,136,0.1);
            border: 2px solid rgba(0,255,136,0.3);
            border-radius: 12px;
            padding: 15px;
            margin: 15px 0;
            text-align: center;
        }
        
        .otp-code {
            font-size: 28px;
            font-weight: 700;
            color: #00ff88;
            letter-spacing: 3px;
            font-family: monospace;
        }
        
        .copy-btn {
            background: rgba(0,255,136,0.2);
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            color: #00ff88;
            cursor: pointer;
            margin-top: 10px;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .info-label { color: #888; font-size: 13px; }
        .info-value { color: #fff; font-size: 13px; }
        
        .message-content {
            background: rgba(0,0,0,0.2);
            padding: 12px;
            border-radius: 8px;
            margin-top: 15px;
            font-size: 13px;
            color: #aaa;
        }
        
        .timestamp { text-align: right; font-size: 11px; color: #666; margin-top: 10px; }
        
        .empty-state { text-align: center; padding: 60px; color: #888; grid-column: 1/-1; }
        .empty-icon { font-size: 64px; margin-bottom: 20px; }
        
        .debug-panel {
            background: rgba(0,0,0,0.5);
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            font-family: monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .debug-log { padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
        
        .refresh-indicator {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 12px;
        }
        
        .pulse {
            width: 10px;
            height: 10px;
            background: #00ff88;
            border-radius: 50%;
            display: inline-block;
            animation: pulse 2s infinite;
            margin-right: 10px;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .tabs { display: flex; gap: 10px; margin: 20px 0; }
        .tab {
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            cursor: pointer;
        }
        .tab.active { background: #00ff88; color: #000; }
        
        @media (max-width: 768px) {
            .header-content { flex-direction: column; }
            .messages-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo">📱 SMS OTP Dashboard</div>
            
            <div class="stats-bar">
                <div class="stat-item">
                    <div class="stat-value">{{ stats.total_otps }}</div>
                    <div class="stat-label">Total OTPs</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ stats.last_check }}</div>
                    <div class="stat-label">Last Check</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ messages|length }}</div>
                    <div class="stat-label">Messages</div>
                </div>
            </div>
            
            <div class="status-badge {{ 'status-online' if stats.is_running else 'status-offline' }}">
                {{ '🟢 Online' if stats.is_running else '🔴 Offline' }}
            </div>
        </div>
    </header>
    
    <div class="container">
        <div>
            <button class="btn btn-primary" onclick="location.reload()">🔄 Refresh</button>
            <button class="btn btn-secondary" onclick="manualCheck()">⚡ Force Check</button>
            <button class="btn btn-danger" onclick="clearAll()">🗑️ Clear All</button>
            <button class="btn btn-secondary" onclick="toggleDebug()">🔧 Debug</button>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('messages')">📨 Messages</div>
            <div class="tab" onclick="showTab('debug')">🔧 Debug Logs</div>
        </div>
        
        <!-- Debug Panel -->
        <div id="debugPanel" class="debug-panel" style="display:none;">
            <h3>🔧 Debug Logs</h3>
            <p><strong>Status:</strong> {{ stats.scraper_status }}</p>
            <p><strong>Last Error:</strong> {{ stats.last_error or 'None' }}</p>
            <hr style="margin: 10px 0; border-color: rgba(255,255,255,0.1);">
            <h4>API Response:</h4>
            <pre style="white-space: pre-wrap;">{{ stats.api_response or 'No response yet' }}</pre>
            <hr style="margin: 10px 0; border-color: rgba(255,255,255,0.1);">
            <h4>Logs:</h4>
            {% for log in debug_logs %}
            <div class="debug-log">{{ log }}</div>
            {% endfor %}
        </div>
        
        <!-- Messages Grid -->
        <div id="messagesPanel" class="messages-grid">
            {% if messages %}
                {% for msg in messages %}
                <div class="message-card">
                    <div class="card-header">
                        <div class="country-info">
                            <span class="country-flag">{{ msg.country_flag }}</span>
                            <span class="country-name">{{ msg.country or 'Unknown' }}</span>
                        </div>
                        <span class="service-badge">{{ msg.service }}</span>
                    </div>
                    
                    <div class="otp-section">
                        <div style="font-size:12px; color:#888;">OTP CODE</div>
                        <div class="otp-code">{{ msg.otp }}</div>
                        <button class="copy-btn" onclick="copyOTP(this, '{{ msg.otp }}')">📋 Copy</button>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">📱 Phone</span>
                        <span class="info-value">{{ msg.phone_masked }}</span>
                    </div>
                    
                    <div class="message-content">{{ msg.raw_message }}</div>
                    <div class="timestamp">⏰ {{ msg.timestamp }}</div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <h3>No messages yet</h3>
                    <p>Waiting for OTP messages...</p>
                    <p style="margin-top:10px; color:#666;">Check Debug panel for details</p>
                </div>
            {% endif %}
        </div>
    </div>
    
    <div class="refresh-indicator">
        <span class="pulse"></span>
        Auto-refresh: <span id="countdown">10</span>s
    </div>

    <script>
        function copyOTP(btn, otp) {
            navigator.clipboard.writeText(otp.replace(/-/g, ''));
            btn.textContent = '✅ Copied!';
            setTimeout(() => btn.textContent = '📋 Copy', 2000);
        }
        
        function manualCheck() {
            fetch('/api/refresh').then(() => location.reload());
        }
        
        function clearAll() {
            if(confirm('Clear all messages?')) {
                fetch('/api/clear').then(() => location.reload());
            }
        }
        
        function toggleDebug() {
            const panel = document.getElementById('debugPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }
        
        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            
            if(tab === 'debug') {
                document.getElementById('debugPanel').style.display = 'block';
                document.getElementById('messagesPanel').style.display = 'none';
            } else {
                document.getElementById('debugPanel').style.display = 'none';
                document.getElementById('messagesPanel').style.display = 'grid';
            }
        }
        
        // Auto-refresh
        let countdown = 10;
        setInterval(() => {
            countdown--;
            document.getElementById('countdown').textContent = countdown;
            if (countdown <= 0) {
                location.reload();
            }
        }, 1000);
    </script>
</body>
</html>
'''

#============================================
# Flask Routes
#============================================

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, 
                                  messages=all_messages, 
                                  stats=bot_stats,
                                  debug_logs=debug_logs)

@app.route('/api/messages')
def api_messages():
    return jsonify({
        'messages': all_messages,
        'stats': bot_stats,
        'debug': debug_logs[:10]
    })

@app.route('/api/refresh')
def api_refresh():
    add_debug("⚡ Manual refresh triggered")
    check_and_update()
    return jsonify({'status': 'ok', 'count': len(all_messages)})

@app.route('/api/clear')
def api_clear():
    global all_messages
    all_messages = []
    otp_filter.clear()
    bot_stats['total_otps'] = 0
    add_debug("🗑️ Cache cleared")
    return jsonify({'status': 'ok'})

@app.route('/api/debug')
def api_debug():
    return jsonify({
        'stats': bot_stats,
        'logs': debug_logs,
        'messages_count': len(all_messages)
    })

#============================================
# Main
#============================================

def main():
    global scraper
    
    add_debug("🚀 Starting SMS OTP Dashboard...")
    
    scraper = create_scraper()
    
    threading.Thread(target=background_monitor, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    add_debug(f"🌐 Dashboard at http://localhost:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == '__main__':
    main()
