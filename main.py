from flask import Flask, render_template_string, request, redirect, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

# ===================== الإعدادات =====================
app = Flask(__name__)
app.secret_key = "super_secret_key"  # <===== غيّره لمفتاحك السري الخاص

UPLOAD_FOLDER = "uploads"
DB = "database.db"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ===================== متغيرات سهلة التعديل =====================
BACKGROUND_URL = "https://i.ibb.co/fdV4Q3qt/background.jpg"
MAIN_CHANNEL_URL = "https://t.me/JX_Codez"
ADMIN_USERNAME = "mohaymen"
ADMIN_PASSWORD = "mohaymen"

# ===================== قاعدة البيانات =====================
def init_db():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        # جدول المستخدمين
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            is_admin INTEGER
        )
        """)
        # جدول الملفات
        cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT
        )
        """)
        # إنشاء حساب المالك لو مش موجود
        cur.execute("SELECT * FROM users WHERE username=?", (ADMIN_USERNAME,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users VALUES (NULL,?,?,1)",
                (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD))
            )
        con.commit()

init_db()

# ===================== HTML تسجيل الدخول =====================
LOGIN_HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login - SELVA ⚡</title>
<style>
    body {{
        margin: 0;
        padding: 0;
        font-family: 'Arial', sans-serif;
        background: url('{BACKGROUND_URL}') no-repeat center center fixed;
        background-size: cover;
        color: #fff;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
    }}
    .login-container {{
        background: rgba(0,0,0,0.8);
        padding: 40px;
        border-radius: 15px;
        text-align: center;
        width: 90%;
        max-width: 360px;
        box-shadow: 0 0 30px rgba(0,0,0,0.9);
    }}
    h2 {{
        margin-bottom: 20px;
        font-size: 32px;
        color: #FFD700;
        text-shadow: 0 0 10px #FFD700, 0 0 20px #FF4500;
        animation: glow 1.5s ease-in-out infinite alternate;
    }}
    @keyframes glow {{
        from {{ text-shadow: 0 0 10px #FFD700, 0 0 20px #FF4500; }}
        to {{ text-shadow: 0 0 20px #FFD700, 0 0 40px #FF6347; }}
    }}
    input {{
        width: 90%;
        padding: 12px;
        margin: 10px 0;
        border-radius: 8px;
        border: none;
        outline: none;
        font-size: 16px;
    }}
    button {{
        width: 95%;
        padding: 12px;
        margin-top: 15px;
        border: none;
        border-radius: 8px;
        background-color: #1E90FF;
        color: #fff;
        font-size: 16px;
        cursor: pointer;
        transition: 0.3s;
    }}
    button:hover {{
        background-color: #00BFFF;
    }}
    .main-channel {{
        margin-top: 20px;
        display: inline-block;
        text-decoration: none;
        color: #FFD700;
        font-weight: bold;
        padding: 10px 25px;
        border: 2px solid #FFD700;
        border-radius: 8px;
        transition: 0.3s;
    }}
    .main-channel:hover {{
        background-color: #FFD700;
        color: #000;
    }}
    @media (max-width: 500px) {{
        h2 {{ font-size: 26px; }}
        input, button {{ font-size: 14px; padding: 10px; }}
    }}
</style>
</head>
<body>
<div class="login-container">
    <h2>SELVA ⚡</h2>
    <form method="post">
        <input name="username" placeholder="Username" required><br>
        <input name="password" type="password" placeholder="Password" required><br>
        <button>Login</button>
    </form>
    <a class="main-channel" href="{MAIN_CHANNEL_URL}" target="_blank">Main Channel</a>
</div>
</body>
</html>
"""

# ===================== لوحة التحكم =====================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard - SELVA ⚡</title>
<style>
body {{ font-family: Arial, sans-serif; background-color: #111; color: #fff; padding: 20px; }}
a {{ color: #1E90FF; text-decoration: none; margin-right: 10px; }}
a:hover {{ text-decoration: underline; }}
input, button {{ padding: 8px; margin: 5px 0; border-radius: 6px; border: none; }}
button {{ cursor: pointer; background-color: #1E90FF; color: #fff; }}
button:hover {{ background-color: #00BFFF; }}
h2 {{ text-shadow: 0 0 10px #FFD700; }}
</style>
</head>
<body>
<h2>Dashboard - SELVA ⚡</h2>
<a href="/logout">Logout</a>

{% if admin %}
<h3>Create User</h3>
<form method="post" action="/create_user">
<input name="username" placeholder="Username" required>
<input name="password" placeholder="Password" required>
<button>Create</button>
</form>

<h3>Upload File</h3>
<form method="post" action="/upload" enctype="multipart/form-data">
<input type="file" name="file" required>
<button>Upload</button>
</form>
{% endif %}

<h3>Files</h3>
<ul>
{% for f in files %}
<li>
{{f[1]}}
<a href="/download/{{f[1]}}">⬇️ Download</a>
{% if admin %}
<a href="/delete/{{f[0]}}">🗑️ Delete</a>
{% endif %}
</li>
{% endfor %}
</ul>
</body>
</html>
"""

# ===================== Routes =====================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]
        with sqlite3.connect(DB) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE username=?", (user,))
            u = cur.fetchone()
        if u and check_password_hash(u[2], pwd):
            session["user"] = u[1]
            session["admin"] = bool(u[3])
            return redirect("/dashboard")
    return render_template_string(LOGIN_HTML)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM files")
        files = cur.fetchall()
    return render_template_string(DASHBOARD_HTML, files=files, admin=session["admin"])

@app.route("/create_user", methods=["POST"])
def create_user():
    if not session.get("admin"):
        return "ممنوع"
    user = request.form["username"]
    pwd = request.form["password"]
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("INSERT INTO users VALUES (NULL,?,?,0)", (user, generate_password_hash(pwd)))
        con.commit()
    return redirect("/dashboard")

@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("admin"):
        return "ممنوع"
    f = request.files["file"]
    f.save(os.path.join(UPLOAD_FOLDER, f.filename))
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("INSERT INTO files VALUES (NULL,?)", (f.filename,))
        con.commit()
    return redirect("/dashboard")

@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return "ممنوع"
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT filename FROM files WHERE id=?", (id,))
        name = cur.fetchone()[0]
        cur.execute("DELETE FROM files WHERE id=?", (id,))
        con.commit()
    os.remove(os.path.join(UPLOAD_FOLDER, name))
    return redirect("/dashboard")

@app.route("/download/<name>")
def download(name):
    return send_from_directory(UPLOAD_FOLDER, name, as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ===================== تشغيل السيرفر =====================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
