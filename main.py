from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__)
app.secret_key = "super_secret_key"

UPLOAD_FOLDER = "uploads"
DB = "database.db"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= قاعدة البيانات =================
def init_db():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            is_admin INTEGER
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT
        )
        """)

        # إنشاء حساب المالك لو مش موجود
        cur.execute("SELECT * FROM users WHERE username=?", ("mohaymen",))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users VALUES (NULL,?,?,1)",
                ("mohaymen", generate_password_hash("mohaymen"))
            )
        con.commit()

init_db()

# ================= تسجيل الدخول =================
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

# ================= لوحة التحكم =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM files")
        files = cur.fetchall()

    return render_template_string(DASHBOARD_HTML, files=files, admin=session["admin"])

# ================= إنشاء حساب =================
@app.route("/create_user", methods=["POST"])
def create_user():
    if not session.get("admin"):
        return "ممنوع"

    user = request.form["username"]
    pwd = request.form["password"]

    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO users VALUES (NULL,?,?,0)",
            (user, generate_password_hash(pwd))
        )
        con.commit()
    return redirect("/dashboard")

# ================= رفع ملف =================
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

# ================= حذف ملف =================
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

# ================= تحميل =================
@app.route("/download/<name>")
def download(name):
    return send_from_directory(UPLOAD_FOLDER, name, as_attachment=True)

# ================= تسجيل خروج =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= HTML =================
LOGIN_HTML = """
<h2>Login</h2>
<form method="post">
<input name="username" placeholder="Username"><br>
<input name="password" type="password" placeholder="Password"><br>
<button>Login</button>
</form>
"""

DASHBOARD_HTML = """
<h2>Dashboard</h2>
<a href="/logout">Logout</a>

{% if admin %}
<h3>Create User</h3>
<form method="post" action="/create_user">
<input name="username" placeholder="Username">
<input name="password" placeholder="Password">
<button>Create</button>
</form>

<h3>Upload File</h3>
<form method="post" action="/upload" enctype="multipart/form-data">
<input type="file" name="file">
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
"""

# ================= تشغيل =================
app.run(host="0.0.0.0", port=5000)
