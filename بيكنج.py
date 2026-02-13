import os
import logging
import requests
import re
import hashlib
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for
from dotenv import load_dotenv
import threading
import time
from functools import wraps

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'otp-king-secret-key-2026'

#============================================
# Database Setup
#============================================

def init_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  telegram TEXT,
                  country TEXT,
                  role TEXT DEFAULT 'user',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Panel settings table
    c.execute('''CREATE TABLE IF NOT EXISTS panel_settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  panel_url TEXT,
                  panel_username TEXT,
                  panel_password TEXT,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Insert default admin if not exists
    c.execute("SELECT * FROM users WHERE username=?", ('mohaymen',))
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, telegram, country, role) VALUES (?, ?, ?, ?, ?)",
                  ('mohaymen', 'mohaymen', '@mohaymen', 'Egypt', 'owner'))
    
    # Insert default panel settings
    c.execute("SELECT * FROM panel_settings")
    if not c.fetchone():
        c.execute("INSERT INTO panel_settings (panel_url, panel_username, panel_password) VALUES (?, ?, ?)",
                  ('http://198.135.52.238', 'gagaywb66', 'gagaywb66'))
    
    conn.commit()
    conn.close()

init_database()

#============================================
# Login Decorator
#============================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'owner':
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

#============================================
# Video Intro HTML
#============================================

VIDEO_INTRO = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTP KING - Intro</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: 'Arial', sans-serif;
        }
        
        .video-container {
            width: 100%;
            max-width: 600px;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            animation: fadeIn 1s ease;
        }
        
        video {
            width: 100%;
            display: block;
        }
        
        .skip-btn {
            position: absolute;
            bottom: 30px;
            right: 30px;
            background: rgba(255,255,255,0.1);
            color: white;
            border: 1px solid rgba(255,255,255,0.2);
            padding: 12px 30px;
            border-radius: 50px;
            cursor: pointer;
            font-size: 16px;
            backdrop-filter: blur(10px);
            transition: all 0.3s;
        }
        
        .skip-btn:hover {
            background: rgba(255,255,255,0.2);
            transform: scale(1.05);
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.9); }
            to { opacity: 1; transform: scale(1); }
        }
        
        .loading-text {
            color: white;
            text-align: center;
            margin-top: 20px;
            font-size: 18px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="video-container">
        <video id="introVideo" autoplay playsinline>
            <source src="https://drive.google.com/uc?export=download&id=1OGS3-mnoM7Q6P-MTl3GDrtU2_9BvL3Mr" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    </div>
    
    <button class="skip-btn" onclick="skipIntro()">تخطي →</button>
    
    <script>
        const video = document.getElementById('introVideo');
        
        video.addEventListener('ended', function() {
            window.location.href = '/login';
        });
        
        function skipIntro() {
            window.location.href = '/login';
        }
        
        // Auto redirect after 4 seconds
        setTimeout(() => {
            window.location.href = '/login';
        }, 4000);
    </script>
</body>
</html>
'''

#============================================
# Login Page HTML
#============================================

LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTP KING - تسجيل الدخول</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Tajawal', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            width: 100%;
            max-width: 400px;
            padding: 20px;
        }
        
        .login-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 30px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            animation: slideUp 0.5s ease;
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .logo {
            font-size: 48px;
            font-weight: 900;
            color: #00ff88;
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 0 0 20px rgba(0,255,136,0.5);
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        .input-group label {
            display: block;
            color: #fff;
            margin-bottom: 8px;
            font-size: 16px;
            font-weight: 500;
        }
        
        .input-group input {
            width: 100%;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 15px;
            color: #fff;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        .input-group input:focus {
            outline: none;
            border-color: #00ff88;
            background: rgba(0,255,136,0.1);
        }
        
        .btn {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 15px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 15px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00ff88, #00cc6a);
            color: #000;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,255,136,0.4);
        }
        
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .btn-secondary:hover {
            background: rgba(255,255,255,0.15);
        }
        
        .error-message {
            background: rgba(255,68,68,0.2);
            border: 1px solid #ff4444;
            color: #ff4444;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .register-link {
            text-align: center;
            color: #888;
            margin-top: 20px;
        }
        
        .register-link a {
            color: #00ff88;
            text-decoration: none;
            font-weight: 700;
        }
        
        .register-link a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-card">
            <div class="logo">OTP KING</div>
            
            {% if error %}
            <div class="error-message">{{ error }}</div>
            {% endif %}
            
            <form method="POST" action="/login">
                <div class="input-group">
                    <label>👤 اسم المستخدم</label>
                    <input type="text" name="username" required>
                </div>
                
                <div class="input-group">
                    <label>🔐 كلمة المرور</label>
                    <input type="password" name="password" required>
                </div>
                
                <button type="submit" class="btn btn-primary">تسجيل الدخول</button>
            </form>
            
            <button class="btn btn-secondary" onclick="window.location.href='/register'">
                ✨ Create my account
            </button>
            
            <div class="register-link">
                ليس لديك حساب؟ <a href="/register">أنشئ حساب جديد</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

#============================================
# Register Page HTML
#============================================

REGISTER_PAGE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTP KING - إنشاء حساب</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Tajawal', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            width: 100%;
            max-width: 450px;
            padding: 20px;
        }
        
        .register-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 30px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            animation: slideUp 0.5s ease;
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .logo {
            font-size: 36px;
            font-weight: 900;
            color: #00ff88;
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 0 0 20px rgba(0,255,136,0.5);
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        .input-group label {
            display: block;
            color: #fff;
            margin-bottom: 8px;
            font-size: 16px;
            font-weight: 500;
        }
        
        .input-group input, .input-group select {
            width: 100%;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 15px;
            color: #fff;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        .input-group select {
            cursor: pointer;
            option { background: #24243e; }
        }
        
        .input-group input:focus, .input-group select:focus {
            outline: none;
            border-color: #00ff88;
            background: rgba(0,255,136,0.1);
        }
        
        .btn {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 15px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 15px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00ff88, #00cc6a);
            color: #000;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,255,136,0.4);
        }
        
        .error-message {
            background: rgba(255,68,68,0.2);
            border: 1px solid #ff4444;
            color: #ff4444;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .success-message {
            background: rgba(0,255,136,0.2);
            border: 1px solid #00ff88;
            color: #00ff88;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .login-link {
            text-align: center;
            color: #888;
            margin-top: 20px;
        }
        
        .login-link a {
            color: #00ff88;
            text-decoration: none;
            font-weight: 700;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="register-card">
            <div class="logo">إنشاء حساب جديد</div>
            
            {% if error %}
            <div class="error-message">{{ error }}</div>
            {% endif %}
            
            {% if success %}
            <div class="success-message">{{ success }}</div>
            {% endif %}
            
            <form method="POST" action="/register">
                <div class="input-group">
                    <label>👤 اسم المستخدم</label>
                    <input type="text" name="username" required placeholder="أدخل اسم المستخدم">
                </div>
                
                <div class="input-group">
                    <label>🔐 كلمة المرور</label>
                    <input type="password" name="password" required placeholder="أدخل كلمة المرور">
                </div>
                
                <div class="input-group">
                    <label>📱 معرف تليجرام</label>
                    <input type="text" name="telegram" required placeholder="@username">
                </div>
                
                <div class="input-group">
                    <label>🌍 الدولة</label>
                    <select name="country" required>
                        <option value="">اختر دولتك</option>
                        <option value="Egypt">🇪🇬 مصر</option>
                        <option value="Saudi Arabia">🇸🇦 السعودية</option>
                        <option value="UAE">🇦🇪 الإمارات</option>
                        <option value="Kuwait">🇰🇼 الكويت</option>
                        <option value="Qatar">🇶🇦 قطر</option>
                        <option value="Bahrain">🇧🇭 البحرين</option>
                        <option value="Oman">🇴🇲 عمان</option>
                        <option value="Jordan">🇯🇴 الأردن</option>
                        <option value="Palestine">🇵🇸 فلسطين</option>
                        <option value="Lebanon">🇱🇧 لبنان</option>
                        <option value="Iraq">🇮🇶 العراق</option>
                        <option value="Yemen">🇾🇪 اليمن</option>
                        <option value="Syria">🇸🇾 سوريا</option>
                        <option value="Libya">🇱🇾 ليبيا</option>
                        <option value="Tunisia">🇹🇳 تونس</option>
                        <option value="Algeria">🇩🇿 الجزائر</option>
                        <option value="Morocco">🇲🇦 المغرب</option>
                        <option value="Sudan">🇸🇩 السودان</option>
                    </select>
                </div>
                
                <button type="submit" class="btn btn-primary">✨ Create</button>
            </form>
            
            <div class="login-link">
                لديك حساب بالفعل؟ <a href="/login">تسجيل الدخول</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

#============================================
# Account Logs Page HTML (Owner Only)
#============================================

ACCOUNT_LOGS_PAGE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTP KING - سجلات الحسابات</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Tajawal', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            color: #fff;
        }
        
        .header {
            background: rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .logo {
            font-size: 28px;
            font-weight: 900;
            color: #00ff88;
        }
        
        .nav-buttons {
            display: flex;
            gap: 10px;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00ff88, #00cc6a);
            color: #000;
        }
        
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        
        .btn-danger {
            background: #ff4444;
            color: #fff;
        }
        
        .btn-warning {
            background: #ffbb33;
            color: #000;
        }
        
        .container {
            max-width: 1200px;
            margin: 30px auto;
            padding: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 36px;
            font-weight: 900;
            color: #00ff88;
        }
        
        .stat-label {
            font-size: 16px;
            color: #aaa;
        }
        
        .users-table {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .table-header {
            display: grid;
            grid-template-columns: 0.5fr 1fr 1fr 1fr 1fr 0.8fr 2fr;
            background: rgba(0,255,136,0.2);
            padding: 15px;
            font-weight: 700;
            color: #00ff88;
        }
        
        .table-row {
            display: grid;
            grid-template-columns: 0.5fr 1fr 1fr 1fr 1fr 0.8fr 2fr;
            padding: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            align-items: center;
        }
        
        .table-row:hover {
            background: rgba(255,255,255,0.05);
        }
        
        .role-badge {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            display: inline-block;
        }
        
        .role-owner { background: linear-gradient(135deg, #ffbb33, #ff8800); color: #000; }
        .role-admin { background: linear-gradient(135deg, #00ff88, #00cc6a); color: #000; }
        .role-user { background: rgba(255,255,255,0.2); color: #fff; }
        
        .action-btn {
            padding: 5px 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
            margin: 2px;
        }
        
        .action-btn.edit { background: #00ff88; color: #000; }
        .action-btn.delete { background: #ff4444; color: #fff; }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal-content {
            background: linear-gradient(135deg, #0f0c29, #302b63);
            padding: 40px;
            border-radius: 20px;
            max-width: 400px;
            width: 90%;
        }
        
        .search-box {
            margin-bottom: 20px;
        }
        
        .search-box input {
            width: 100%;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            color: #fff;
            font-size: 16px;
        }
        
        @media (max-width: 768px) {
            .table-header, .table-row {
                grid-template-columns: 1fr;
                gap: 10px;
            }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo">👑 OTP KING - لوحة التحكم</div>
            <div class="nav-buttons">
                <a href="/dashboard" class="btn btn-secondary">⬅️ العودة للوحة</a>
                <a href="/add-admin" class="btn btn-primary">➕ إضافة أدمن</a>
                <a href="/logout" class="btn btn-danger">🚪 تسجيل الخروج</a>
            </div>
        </div>
    </header>
    
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_users }}</div>
                <div class="stat-label">إجمالي المستخدمين</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_admins }}</div>
                <div class="stat-label">عدد الأدمن</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.new_today }}</div>
                <div class="stat-label">جديد اليوم</div>
            </div>
        </div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="🔍 بحث عن مستخدم..." onkeyup="searchUsers()">
        </div>
        
        <div class="users-table">
            <div class="table-header">
                <div>#</div>
                <div>👤 المستخدم</div>
                <div>🔐 كلمة المرور</div>
                <div>📱 تليجرام</div>
                <div>🌍 الدولة</div>
                <div>⭐ الصلاحية</div>
                <div>⚡ الإجراءات</div>
            </div>
            
            <div id="usersList">
                {% for user in users %}
                <div class="table-row" data-username="{{ user.username }}" data-country="{{ user.country }}">
                    <div>{{ loop.index }}</div>
                    <div>{{ user.username }}</div>
                    <div>{{ user.password }}</div>
                    <div>{{ user.telegram }}</div>
                    <div>{{ user.country }}</div>
                    <div>
                        <span class="role-badge role-{{ user.role }}">
                            {% if user.role == 'owner' %}👑 مالك
                            {% elif user.role == 'admin' %}⚡ أدمن
                            {% else %}👤 مستخدم{% endif %}
                        </span>
                    </div>
                    <div>
                        {% if user.role != 'owner' %}
                        <button class="action-btn edit" onclick="editPassword('{{ user.username }}')">🔑 تغيير</button>
                        <button class="action-btn edit" onclick="makeAdmin('{{ user.username }}')">⭐ أدمن</button>
                        <button class="action-btn delete" onclick="deleteUser('{{ user.username }}')">🗑️ حذف</button>
                        {% else %}
                        <span style="color:#888;">لا يمكن التعديل</span>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <!-- Edit Password Modal -->
    <div id="editModal" class="modal">
        <div class="modal-content">
            <h2 style="color:#00ff88; margin-bottom:20px;">تغيير كلمة المرور</h2>
            <input type="hidden" id="editUsername">
            <div class="input-group">
                <label style="color:#fff;">كلمة المرور الجديدة</label>
                <input type="password" id="newPassword" style="width:100%; padding:10px; margin:10px 0; background:rgba(255,255,255,0.1); border:1px solid #00ff88; border-radius:5px; color:#fff;">
            </div>
            <button class="btn btn-primary" style="width:100%;" onclick="savePassword()">حفظ التغييرات</button>
            <button class="btn btn-secondary" style="width:100%; margin-top:10px;" onclick="closeModal()">إلغاء</button>
        </div>
    </div>
    
    <script>
        function searchUsers() {
            const searchText = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('.table-row');
            
            rows.forEach(row => {
                const username = row.dataset.username.toLowerCase();
                const country = row.dataset.country.toLowerCase();
                
                if (username.includes(searchText) || country.includes(searchText)) {
                    row.style.display = 'grid';
                } else {
                    row.style.display = 'none';
                }
            });
        }
        
        function editPassword(username) {
            document.getElementById('editUsername').value = username;
            document.getElementById('editModal').style.display = 'flex';
        }
        
        function closeModal() {
            document.getElementById('editModal').style.display = 'none';
        }
        
        function savePassword() {
            const username = document.getElementById('editUsername').value;
            const newPassword = document.getElementById('newPassword').value;
            
            if (!newPassword) {
                alert('الرجاء إدخال كلمة المرور الجديدة');
                return;
            }
            
            fetch('/api/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username, password: newPassword })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('تم تغيير كلمة المرور بنجاح');
                    location.reload();
                } else {
                    alert('حدث خطأ: ' + data.error);
                }
            });
        }
        
        function makeAdmin(username) {
            if (confirm('هل أنت متأكد من ترقية هذا المستخدم إلى أدمن؟')) {
                fetch('/api/make-admin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('تم ترقية المستخدم إلى أدمن');
                        location.reload();
                    } else {
                        alert('حدث خطأ: ' + data.error);
                    }
                });
            }
        }
        
        function deleteUser(username) {
            if (confirm('هل أنت متأكد من حذف هذا المستخدم؟')) {
                fetch('/api/delete-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('تم حذف المستخدم بنجاح');
                        location.reload();
                    } else {
                        alert('حدث خطأ: ' + data.error);
                    }
                });
            }
        }
    </script>
</body>
</html>
'''

#============================================
# Add Admin Page HTML (Owner Only)
#============================================

ADD_ADMIN_PAGE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTP KING - إضافة أدمن</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Tajawal', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            width: 100%;
            max-width: 450px;
            padding: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 30px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        
        h1 {
            color: #00ff88;
            text-align: center;
            margin-bottom: 30px;
            font-size: 32px;
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        .input-group label {
            display: block;
            color: #fff;
            margin-bottom: 8px;
            font-size: 16px;
        }
        
        .input-group input {
            width: 100%;
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 15px;
            color: #fff;
            font-size: 16px;
        }
        
        .input-group input:focus {
            outline: none;
            border-color: #00ff88;
        }
        
        .btn {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 15px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 10px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00ff88, #00cc6a);
            color: #000;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,255,136,0.4);
        }
        
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        
        .message {
            background: rgba(0,255,136,0.2);
            border: 1px solid #00ff88;
            color: #00ff88;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .error {
            background: rgba(255,68,68,0.2);
            border: 1px solid #ff4444;
            color: #ff4444;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>➕ إضافة أدمن جديد</h1>
            
            {% if message %}
            <div class="message">{{ message }}</div>
            {% endif %}
            
            {% if error %}
            <div class="message error">{{ error }}</div>
            {% endif %}
            
            <form method="POST" action="/add-admin">
                <div class="input-group">
                    <label>👤 اسم المستخدم</label>
                    <input type="text" name="username" required>
                </div>
                
                <div class="input-group">
                    <label>🔐 كلمة المرور</label>
                    <input type="password" name="password" required>
                </div>
                
                <div class="input-group">
                    <label>📱 تليجرام</label>
                    <input type="text" name="telegram" required placeholder="@username">
                </div>
                
                <div class="input-group">
                    <label>🌍 الدولة</label>
                    <input type="text" name="country" required placeholder="مصر">
                </div>
                
                <button type="submit" class="btn btn-primary">✅ إضافة أدمن</button>
                <button type="button" class="btn btn-secondary" onclick="window.location.href='/account-logs'">⬅️ رجوع</button>
            </form>
        </div>
    </div>
</body>
</html>
'''

#============================================
# Main Dashboard HTML (Modified Original)
#============================================

DASHBOARD_TEMPLATE = '''
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
        
        .logo { 
            font-size: 24px; 
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
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
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary { background: linear-gradient(135deg, #00ff88, #00cc6a); color: #000; }
        .btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
        .btn-danger { background: #ff4444; color: #fff; }
        .btn-warning { background: #ffbb33; color: #000; }
        
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
            max-height: 100px;
            overflow-y: auto;
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
            z-index: 1000;
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
        
        .tabs { display: flex; gap: 10px; margin: 20px 0; flex-wrap: wrap; }
        .tab {
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .tab.active { background: #00ff88; color: #000; }
        
        .user-info {
            background: rgba(255,255,255,0.05);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
        }
        
        @media (max-width: 768px) {
            .header-content { flex-direction: column; }
            .messages-grid { grid-template-columns: 1fr; }
            .tabs { justify-content: center; }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo">
                📱 SMS OTP Dashboard
                <span class="user-info">{{ session.username }} ({{ session.role }})</span>
            </div>
            
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
        <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: space-between; margin-bottom: 20px;">
            <div>
                <button class="btn btn-primary" onclick="location.reload()">🔄 Refresh</button>
                <button class="btn btn-secondary" onclick="manualCheck()">⚡ Force Check</button>
                <button class="btn btn-danger" onclick="clearAll()">🗑️ Clear All</button>
                <button class="btn btn-secondary" onclick="toggleDebug()">🔧 Debug</button>
            </div>
            <div>
                {% if session.role == 'owner' %}
                <a href="/account-logs" class="btn btn-warning">📋 Account Logs</a>
                <a href="/add-admin" class="btn btn-primary">➕ Add Admin</a>
                {% endif %}
                <a href="/logout" class="btn btn-danger">🚪 Logout</a>
            </div>
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
            <p><strong>Panel URL:</strong> {{ panel_url }}</p>
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
                    
                    <div class="info-row">
                        <span class="info-label">🆔 ID</span>
                        <span class="info-value">{{ msg.id }}</span>
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
# Original OTP System Code (Modified)
#============================================

PANEL_URL = "http://198.135.52.238"
PANEL_USERNAME = "gagaywb66"
PANEL_PASSWORD = "gagaywb66"

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
    'sudan': '🇸🇩', 'sd': '🇸🇩',
}

#============================================
# Database Functions
#============================================

def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_panel_settings():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM panel_settings ORDER BY id DESC LIMIT 1")
    result = c.fetchone()
    conn.close()
    if result:
        return {
            'panel_url': result['panel_url'],
            'panel_username': result['panel_username'],
            'panel_password': result['panel_password']
        }
    return {
        'panel_url': PANEL_URL,
        'panel_username': PANEL_USERNAME,
        'panel_password': PANEL_PASSWORD
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
    def __init__(self):
        settings = get_panel_settings()
        self.base_url = settings['panel_url'].rstrip('/')
        self.username = settings['panel_username']
        self.password = settings['panel_password']
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
            
            add_debug(f"📥 Response type: {type(data)}")
            
            if isinstance(data, list):
                messages = data
                add_debug(f"📥 Response is a list with {len(messages)} items")
            elif isinstance(data, dict):
                add_debug(f"📥 Response keys: {list(data.keys())}")
                messages = data.get('messages', data.get('sms', data.get('data', [])))
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
            content = msg.get('message', msg.get('content', msg.get('text', '')))
            otp = self._extract_otp(content)
            
            phone = msg.get('phone_number', msg.get('Number', msg.get('number', msg.get('phone', 'Unknown'))))
            country_name = msg.get('country', msg.get('Country', ''))
            country_flag = self._get_country_flag(country_name)
            
            service = (
                msg.get('sender', msg.get('service', msg.get('Service', ''))) or 
                self._detect_service(content)
            )
            
            timestamp = msg.get('received_at', msg.get('created_at', msg.get('timestamp', '')))
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
                'service': service or 'SMS Service',
                'country': country_name or 'Unknown',
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
            r'(?:code|kode|otp|كود)[:\s]*(\d{4,8})',
            r'(\d{6})',
            r'(\d{4,8})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.I)
            if match:
                return match.group(1).replace(' ', '-').replace('-', '')
        return 'N/A'
    
    def _detect_service(self, content):
        if not content:
            return 'Unknown'
        
        services = {
            'whatsapp': 'WhatsApp', 'telegram': 'Telegram',
            'facebook': 'Facebook', 'instagram': 'Instagram',
            'twitter': 'Twitter', 'google': 'Google',
            'tiktok': 'TikTok', 'snapchat': 'Snapchat',
            'adobe': 'Adobe', 'microsoft': 'Microsoft',
            'apple': 'Apple', 'amazon': 'Amazon',
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
        api = PanelAPI()
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
        if len(self.cache) > 1000:
            self.cache = set(list(self.cache)[-500:])
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
# Flask Routes - Authentication
#============================================

@app.route('/')
def index():
    return render_template_string(VIDEO_INTRO)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(LOGIN_PAGE, error="اسم المستخدم أو كلمة المرور غير صحيحة")
    
    return render_template_string(LOGIN_PAGE)

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        telegram = request.form.get('telegram')
        country = request.form.get('country')
        
        conn = get_db()
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO users (username, password, telegram, country, role) VALUES (?, ?, ?, ?, 'user')",
                     (username, password, telegram, country))
            conn.commit()
            success = "تم إنشاء الحساب بنجاح! يمكنك تسجيل الدخول الآن"
            return render_template_string(REGISTER_PAGE, success=success)
        except sqlite3.IntegrityError:
            error = "اسم المستخدم موجود بالفعل"
            return render_template_string(REGISTER_PAGE, error=error)
        finally:
            conn.close()
    
    return render_template_string(REGISTER_PAGE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

#============================================
# Flask Routes - Dashboard
#============================================

@app.route('/dashboard')
@login_required
def dashboard():
    settings = get_panel_settings()
    return render_template_string(DASHBOARD_TEMPLATE, 
                                  messages=all_messages, 
                                  stats=bot_stats,
                                  debug_logs=debug_logs,
                                  session=session,
                                  panel_url=settings['panel_url'])

@app.route('/account-logs')
@owner_required
def account_logs():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()
    
    stats = {
        'total_users': len(users),
        'total_admins': len([u for u in users if u['role'] in ['admin', 'owner']]),
        'new_today': len([u for u in users if u['created_at'].startswith(datetime.now().strftime('%Y-%m-%d'))])
    }
    
    return render_template_string(ACCOUNT_LOGS_PAGE, users=users, stats=stats)

@app.route('/add-admin', methods=['GET', 'POST'])
@owner_required
def add_admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        telegram = request.form.get('telegram')
        country = request.form.get('country')
        
        conn = get_db()
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO users (username, password, telegram, country, role) VALUES (?, ?, ?, ?, 'admin')",
                     (username, password, telegram, country))
            conn.commit()
            return render_template_string(ADD_ADMIN_PAGE, message="✅ تم إضافة الأدمن بنجاح")
        except sqlite3.IntegrityError:
            return render_template_string(ADD_ADMIN_PAGE, error="❌ اسم المستخدم موجود بالفعل")
        finally:
            conn.close()
    
    return render_template_string(ADD_ADMIN_PAGE)

#============================================
# API Routes
#============================================

@app.route('/api/messages')
@login_required
def api_messages():
    return jsonify({
        'messages': all_messages,
        'stats': bot_stats,
        'debug': debug_logs[:10]
    })

@app.route('/api/refresh')
@login_required
def api_refresh():
    add_debug("⚡ Manual refresh triggered")
    check_and_update()
    return jsonify({'status': 'ok', 'count': len(all_messages)})

@app.route('/api/clear')
@login_required
def api_clear():
    global all_messages
    all_messages = []
    otp_filter.clear()
    bot_stats['total_otps'] = 0
    add_debug("🗑️ Cache cleared")
    return jsonify({'status': 'ok'})

@app.route('/api/debug')
@login_required
def api_debug():
    return jsonify({
        'stats': bot_stats,
        'logs': debug_logs,
        'messages_count': len(all_messages)
    })

@app.route('/api/change-password', methods=['POST'])
@owner_required
def change_password():
    data = request.json
    username = data.get('username')
    new_password = data.get('password')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/make-admin', methods=['POST'])
@owner_required
def make_admin():
    data = request.json
    username = data.get('username')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET role='admin' WHERE username=?", (username,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/delete-user', methods=['POST'])
@owner_required
def delete_user():
    data = request.json
    username = data.get('username')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=? AND role!='owner'", (username,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

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
