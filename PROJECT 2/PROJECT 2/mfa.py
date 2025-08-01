from flask import Flask, render_template_string, request, redirect, session
import pyotp
import qrcode
import io
import base64
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# --- Initialize SQLite DB ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            otp_secret TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Templates ---
register_template = '''<!DOCTYPE html>
<html><head><title>Register</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-dark text-white d-flex justify-content-center align-items-center vh-100">
<div class="card p-4 rounded" style="width: 350px; background-color: rgb(255, 102, 0);">
    <h3 class="text-center">PANJIKARAN KAREIN</h3>
    {% if error %}
    <div class="alert alert-danger text-center fw-bold">{{ error }}</div>
    {% endif %}
    <form method="POST">
        <div class="mb-3">
            <label>Upyokta Naam</label>
            <input name="username" class="form-control" style="background-color: rgb(151, 34, 169);" required>
        </div>
        <div class="mb-3">
            <label>Saanketik Shabd</label>
            <input type="password" name="password" class="form-control" style="background-color: rgb(151, 34, 169);" required>
        </div>
        <button class="btn btn-warning w-100 mb-3 fw-bold">PANJIKARAN</button>
    </form>
    {% if qr_code %}
    <div class="text-center">
        <h6>Scan QR with Authenticator App</h6>
        {{ qr_code|safe }}
    </div>
    {% endif %}
</div>
</body></html>'''

login_template = '''<!DOCTYPE html>
<html><head><title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-dark text-black d-flex justify-content-center align-items-center vh-100">
<style>
button {
    width: 100%;
    background-color: hsl(49deg 98% 60%);
    font-weight: bold;
    border: solid 2px white;
    color: white;
    border-radius: 50px;
}
</style>
<div class="card p-4 rounded" style="width: 300px; background-color: rgb(255, 102, 0);">
    <h3 class="text-center text-black">LAAG IN KRE G</h3>
    <form method="POST">
        <div class="mb-3">
            <label class="text-black fw-bold">UPYOKTANAAM</label>
            <input name="username" class="form-control" style="background-color: rgb(151, 34, 169); font-weight: bold;" required>
        </div>
        <div class="mb-3">
            <label class="text-black fw-bold">SAANKETIK SHABD</label>
            <input type="password" name="password" class="form-control" style="background-color: rgb(151, 34, 169); font-weight: bold;" required>
        </div>
        <button type="submit">Ehaan Dabayiye G</button>
    </form>
</div>
</body></html>'''

dashboard_template = '''<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #1f1c2c, #928dab);
            color: white;
            font-family: 'Segoe UI', sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            animation: fadeIn 1.5s ease-in-out;
        }
        .dashboard-box {
            background-color: rgba(0,0,0,0.7);
            padding: 30px 40px;
            border-radius: 20px;
            box-shadow: 0 0 25px rgba(255, 255, 255, 0.2);
            text-align: center;
            backdrop-filter: blur(8px);
        }
        h1 {
            font-size: 36px;
            margin-bottom: 20px;
            color: #fcd34d;
        }
        .username {
            font-weight: bold;
            font-size: 22px;
            color: #93c5fd;
        }
        .logout-btn {
            margin-top: 25px;
            padding: 10px 20px;
            font-weight: bold;
            border: none;
            background-color: #ef4444;
            color: white;
            border-radius: 10px;
            transition: background-color 0.3s ease;
        }
        .logout-btn:hover {
            background-color: #dc2626;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="dashboard-box">
        <h1>👋 Swagat Hai!</h1>
        <p class="username">Logged in as: {{ username }}</p>
        <p>Yahan aake mast mauj lo 😎</p>
        <form action="/logout" method="post">
            <button type="submit" class="logout-btn">Logout</button>
        </form>
    </div>
</body>
</html>'''

# --- Routes ---
@app.route('/')
def index():
    return redirect('/register')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        # Check if username already exists
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        existing_user = c.fetchone()

        if existing_user:
            conn.close()
            return render_template_string(register_template, qr_code='', error='Username already exists. Please try another.')

        # Register new user
        otp_secret = pyotp.random_base32()
        c.execute('INSERT INTO users (username, password, otp_secret) VALUES (?, ?, ?)', (username, password, otp_secret))
        conn.commit()
        conn.close()

        # Generate QR Code
        totp_uri = pyotp.TOTP(otp_secret).provisioning_uri(name=username, issuer_name="MyApp")
        img = qrcode.make(totp_uri)
        buf = io.BytesIO()
        img.save(buf)
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        qr_code = f'''
        <div class="text-center mt-3"> 
        <img src="data:image/png;base64,{img_b64}" style="width: 180px; height: 180px; border: 4px dashed white; border-radius: 16px; box-shadow: 0 0 10px #000;">
        </div>
        '''
        return render_template_string(register_template, qr_code=qr_code, error='')

    return render_template_string(register_template, qr_code='', error='')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT password FROM users WHERE username=?', (username,))
        result = c.fetchone()
        conn.close()
        if result and result[0] == password:
            session['username'] = username
            return redirect('/otp')
    return render_template_string(login_template)

@app.route('/otp', methods=['GET', 'POST'])
def otp():
    if 'username' not in session:
        return redirect('/login')

    if request.method == 'POST':
        otp_input = request.form['otp']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT otp_secret FROM users WHERE username=?', (session['username'],))
        result = c.fetchone()
        conn.close()

        if result:
            totp = pyotp.TOTP(result[0])
            if totp.verify(otp_input):
                return '''
                <!DOCTYPE html>
                <html><head><title>SUS Login</title></head>
                <body style="background:#111; color:#0f0; font-family:'Courier New'; text-align:center; padding:100px;">
                    <h1>🔒 SUS Login Detected 😳</h1>
                    <p>Redirecting to dashboard...</p>
                    <script>setTimeout(() => { window.location.href = "/dashboard"; }, 4000);</script>
                </body></html>
                '''
        return "<h2 style='color:red; text-align:center;'>Invalid OTP</h2>"

    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>OTP Verification</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="bg-dark text-white d-flex justify-content-center align-items-center vh-100">
    <div class="card p-4 rounded" style="width: 300px; background-color: rgb(255, 102, 0);">
        <h3 class="text-center fw-bold">AA T P DAALE</h3>
        <form method="POST">
            <div class="mb-3">
                <label class="fw-bold">Enter AA T P</label>
                <input name="otp" class="form-control" style="background-color: rgb(151, 34, 169);" required>
            </div>
            <button class="btn btn-light w-100 fw-bold" style="background-color: rgb(151, 34, 169);">DAAL DIYA</button>
        </form>
    </div>
    </body></html>
    ''')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    return render_template_string(dashboard_template, username=session['username'])

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return redirect('/login')

# --- Run App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
