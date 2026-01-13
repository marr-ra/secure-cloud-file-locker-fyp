"""
Migration script: read rows from MySQL 'files' and 'users' and write them to Firestore.
Run once (make a backup first).

Set environment variable FIREBASE_CREDENTIALS to path of your service account JSON.

Install:
    pip install firebase-admin mysql-connector-python
"""
import os
import uuid
import mysql.connector
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# MySQL connection - change credentials to match your local DB
mysql_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'secure_file_locker'
}

FIREBASE_CRED_PATH = os.environ.get('FIREBASE_CREDENTIALS')
if not FIREBASE_CRED_PATH:
    raise RuntimeError("Set FIREBASE_CREDENTIALS env var to serviceAccount JSON path")

cred = credentials.Certificate(FIREBASE_CRED_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

def migrate_users(conn):
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    users_ref = db.collection('users')
    for r in rows:
        # Use username as doc id (change if you have another primary key)
        doc_id = r.get('username') or str(r.get('id') or uuid.uuid4())
        users_ref.document(doc_id).set({
            'username': r.get('username'),
            'password': r.get('password'),
            'role': r.get('role'),
            # copy other fields as needed
        })
    cur.close()

def migrate_files(conn):
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM files")
    rows = cur.fetchall()
    files_ref = db.collection('files')
    for r in rows:
        owner = r.get('owner')
        filename = r.get('filename')
        doc_id = f"{owner}::{filename}"
        upload_time = r.get('upload_time')
        # If upload_time is datetime, Firestore accepts it; else convert/parse
        files_ref.document(doc_id).set({
            'filename': filename,
            'filesize': r.get('filesize'),
            'upload_time': upload_time,
            'owner': owner,
            'encryption_status': r.get('encryption_status')
        })
    cur.close()

def main():
    conn = mysql.connector.connect(**mysql_config)
    try:
        migrate_users(conn)
        migrate_files(conn)
        print("Migration complete.")
    finally:
        conn.close()

if __name__ == '__main__':
    main()