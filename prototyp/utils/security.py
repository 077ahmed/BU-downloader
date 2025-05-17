# utils/security.py
from flask_wtf.csrf import validate_csrf
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re

def validate_csrf_token(form_token):
    try:
        validate_csrf(form_token)
        return True
    except:
        return False

def sanitize_input(text):
    return re.sub(r'[^a-zA-Z0-9-_/. ]', '', text).strip()

def get_user_id(username, db_path):
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            user = conn.execute("SELECT id FROM users WHERE username = ?", (sanitize_input(username),)).fetchone()
        return user['id'] if user else None
    except sqlite3.Error:
        return None

def validate_password_complexity(password):
    if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'[0-9]', password):
        return False
    return True

def create_password_hash(password):
    if not validate_password_complexity(password):
        raise ValueError("Password must be at least 8 characters and include upper, lower, and numeric characters.")
    return generate_password_hash(password)

def verify_password_hash(stored_hash, provided_password):
    return check_password_hash(stored_hash, provided_password)
