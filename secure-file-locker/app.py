from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
from datetime import datetime
import firestore_adapter as db_adapter  # new adapter

app = Flask(__name__)
app.secret_key = "fyp_secret_key"

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# (No more MySQL connection here; Firestore adapter handles DB)

# ---------- ROUTES ----------

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = db_adapter.get_user_by_credentials(username, password)

        if user:
            session['user'] = username
            session['role'] = user.get('role', 'user')

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

    files = db_adapter.get_files_for_owner(session['user'])
    return render_template('dashboard.html', files=files)

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    files = db_adapter.get_all_files()
    return render_template('admin_dashboard.html', files=files)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = file.filename
            # Ensure upload folder exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            filesize = os.path.getsize(path)
            upload_time = datetime.now()

            db_adapter.insert_file(
                filename=filename,
                filesize=filesize,
                upload_time=upload_time,
                owner=session['user'],
                encryption_status="Encrypted (Prototype)"
            )

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

        db_adapter.delete_file(filename=filename, owner=session['user'])

    return redirect(url_for('dashboard'))

# ---------- RUN ----------
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    app.run(debug=True)