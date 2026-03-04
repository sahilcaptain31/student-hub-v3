from flask import Flask, render_template, request, redirect, session, send_from_directory, jsonify
import sqlite3, os

app = Flask(__name__)

# SECURITY: Secret key environment se aayegi, hosting par 'SECRET_KEY' set karna
app.secret_key = os.getenv("SECRET_KEY", "dev_mode_only_key_123")

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# DATABASE PATH: PythonAnywhere ya Render par error na aaye isliye absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

def get_db():
    # check_same_thread=False server hosting ke liye zaroori hai
    conn = sqlite3.connect(DB_PATH, check_same_thread=False) 
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                    (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, 
                     role TEXT DEFAULT 'user', level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0)''')
    conn.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, subject TEXT, filename TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS pyq (id INTEGER PRIMARY KEY, subject TEXT, filename TEXT)")
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    conn = get_db()
    leaders = conn.execute("SELECT username, level FROM users ORDER BY level DESC, xp DESC LIMIT 5").fetchall()
    return render_template("index.html", leaders=leaders)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u, p = request.form["username"], request.form["password"]
        secret_input = request.form.get("admin_secret", "")
        
        # STRICT SECURITY: Agar server par ADMIN_CODE set nahi hai, toh None rahega
        # Matlab koi bhi random guess admin nahi ban sakta.
        MASTER_ADMIN_CODE = os.getenv("ADMIN_CODE") 
        
        # Logic: Input match hona chahiye aur MASTER_CODE khali nahi hona chahiye
        if MASTER_ADMIN_CODE and secret_input == MASTER_ADMIN_CODE:
            role = 'admin'
        else:
            role = 'user'
        
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (u, p, role))
            conn.commit()
            return redirect("/login")
        except: return "Username Already Exists!"
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u, p = request.form["username"], request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p)).fetchone()
        if user:
            session["user"], session["role"] = user["username"], user["role"]
            return redirect("/")
        return "Wrong ID or Password!"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/admin")
def admin():
    if session.get("role") != "admin": return "403: Restricted!", 403
    conn = get_db()
    return render_template("admin.html", 
                           users=conn.execute("SELECT * FROM users").fetchall(),
                           notes=conn.execute("SELECT * FROM notes").fetchall(),
                           pyqs=conn.execute("SELECT * FROM pyq").fetchall())

@app.route("/upload", methods=["POST"])
def upload():
    if session.get("role") == "admin":
        subj, type, file = request.form["subject"], request.form["type"], request.files["file"]
        if file and file.filename != '':
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], file.filename))
            conn = get_db()
            conn.execute(f"INSERT INTO {type} (subject, filename) VALUES (?, ?)", (subj, file.filename))
            conn.commit()
    return redirect("/admin")

@app.route("/update_xp", methods=["POST"])
def update_xp():
    if "user" in session:
        data = request.json
        conn = get_db()
        conn.execute("UPDATE users SET level=?, xp=? WHERE username=?", (data['level'], data['xp'], session['user']))
        conn.commit()
    return jsonify({"status": "ok"})

@app.route("/notes")
def notes():
    items = get_db().execute("SELECT * FROM notes").fetchall()
    return render_template("notes.html", items=items)

@app.route("/pyq")
def pyq():
    items = get_db().execute("SELECT * FROM pyq").fetchall()
    return render_template("pyq.html", items=items)

@app.route("/view/<filename>")
def view_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/profile")
def profile(): return render_template("profile.html")

@app.route("/tools")
def tools(): return render_template("tools.html")

@app.route("/schedule")
def schedule(): return render_template("schedule.html")

if __name__ == "__main__":
    app.run(debug=True)