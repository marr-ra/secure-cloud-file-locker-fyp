from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = "fyp_secret_key"

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------- DATABASE CONNECTION ----------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="secure_file_locker"
)
cursor = db.cursor(dictionary=True)

# ---------- ROUTES ----------

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()

        if user:
            session['user'] = username
            session['role'] = user['role']

            return redirect(url_for('dashboard'))
        else:
            return render_template("login.html", error="Invalid username or password")


    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    if session['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT * FROM files WHERE owner=%s", (session['user'],))
    files = cursor.fetchall()
    return render_template('dashboard.html', files=files)

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    cursor.execute("SELECT * FROM files")
    files = cursor.fetchall()
    return render_template('admin_dashboard.html', files=files)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = file.filename
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            filesize = os.path.getsize(path)
            upload_time = datetime.now()

            cursor.execute(
                "INSERT INTO files (filename, filesize, upload_time, owner, encryption_status) "
                "VALUES (%s, %s, %s, %s, %s)",
                (filename, filesize, upload_time, session['user'], "Encrypted (Prototype)")
            )
            db.commit()

            return redirect(url_for('dashboard'))

    return render_template('upload.html')

@app.route('/download/<filename>')
def download(filename):
    if 'user' not in session:
        return redirect(url_for('login'))

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/delete/<filename>')
def delete(filename):
    if 'user' not in session:
        return redirect(url_for('login'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if os.path.exists(file_path):
        os.remove(file_path)

        cursor.execute(
            "DELETE FROM files WHERE filename=%s AND owner=%s",
            (filename, session['user'])
        )
        db.commit()

    return redirect(url_for('dashboard'))

# ---------- RUN ----------
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    app.run(debug=True)
