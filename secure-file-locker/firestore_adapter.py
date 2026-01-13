import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid

# Initialize Firebase using service account JSON path from env var FIREBASE_CREDENTIALS
FIREBASE_CRED_PATH = os.environ.get('FIREBASE_CREDENTIALS', None)

if not firebase_admin._apps:
    if not FIREBASE_CRED_PATH:
        raise RuntimeError("FIREBASE_CREDENTIALS environment variable not set to serviceAccount JSON path")
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Helper to build a stable document id for files (avoid collisions between owners)
def _file_doc_id(owner: str, filename: str) -> str:
    # Use owner + '::' + filename; if you need stronger uniqueness, use uuid4()
    return f"{owner}::{filename}"

# Users
def get_user_by_credentials(username: str, password: str):
    """
    Return a dict with user fields (including 'role') or None if no match.
    Note: storing plaintext password in Firestore is insecure; this mirrors your current app behavior.
    """
    users_ref = db.collection('users')
    query = users_ref.where('username', '==', username).where('password', '==', password).limit(1).stream()
    for doc in query:
        data = doc.to_dict()
        # Make sure 'username' exists in returned dict for compatibility
        data['id'] = doc.id
        return data
    return None

# Files
def get_files_for_owner(owner: str):
    files_ref = db.collection('files')
    docs = files_ref.where('owner', '==', owner).stream()
    out = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        # Firestore returns python datetime for timestamp fields
        if isinstance(d.get('upload_time'), datetime):
            d['upload_time'] = d['upload_time']  # keep as datetime; templates can format
        out.append(d)
    return out

def get_all_files():
    files_ref = db.collection('files')
    docs = files_ref.stream()
    out = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        out.append(d)
    return out

def insert_file(filename: str, filesize: int, upload_time: datetime, owner: str, encryption_status: str):
    files_ref = db.collection('files')
    doc_id = _file_doc_id(owner, filename)
    data = {
        'filename': filename,
        'filesize': filesize,
        'upload_time': upload_time,
        'owner': owner,
        'encryption_status': encryption_status
    }
    files_ref.document(doc_id).set(data)
    return doc_id

def delete_file(filename: str, owner: str) -> bool:
    files_ref = db.collection('files')
    doc_id = _file_doc_id(owner, filename)
    doc_ref = files_ref.document(doc_id)
    if doc_ref.get().exists:
        doc_ref.delete()
        return True
    return False

# Optional helper: create a user (useful for manual bootstrap)
def create_user(username: str, password: str, role: str = 'user', **extra):
    users_ref = db.collection('users')
    doc_id = username  # simple choice; change as needed
    data = {'username': username, 'password': password, 'role': role}
    data.update(extra)
    users_ref.document(doc_id).set(data)
    return doc_id