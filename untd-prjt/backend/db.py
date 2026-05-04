import sqlite3
import os
import hashlib
import secrets
import time
from pathlib import Path

# Use the same directory as this file for the database
DB_PATH = Path(__file__).parent / "users.db"

def get_connection():
    # Return a connection with dict-like rows
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)
    
    # Create Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()

def hash_password(password: str, salt: str) -> str:
    # Use PBKDF2 for basic hashing
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def create_user(username: str, password: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "error": "Username already exists"}
        
    salt = secrets.token_hex(16)
    hashed_pw = hash_password(password, salt)
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
            (username, hashed_pw, salt, int(time.time()))
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"success": True, "user_id": user_id}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": "Username already exists"}

def verify_user(username: str, password: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return {"success": False, "error": "Invalid username or password"}
        
    expected_hash = hash_password(password, user["salt"])
    
    if expected_hash == user["password_hash"]:
        conn.close()
        return {"success": True, "user": dict(user)}
    
    conn.close()
    return {"success": False, "error": "Invalid username or password"}

def create_session(user_id: int, days_valid: int = 7) -> str:
    token = secrets.token_hex(32)
    expires_at = int(time.time()) + (days_valid * 24 * 60 * 60)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Optionally delete old sessions for this user to keep DB small
    cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    
    cursor.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at)
    )
    conn.commit()
    conn.close()
    
    return token

def verify_session(token: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT s.*, u.username FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ?", (token,))
    session = cursor.fetchone()
    conn.close()
    
    if not session:
        return {"valid": False}
        
    if int(time.time()) > session["expires_at"]:
        # Session expired
        return {"valid": False}
        
    return {"valid": True, "user_id": session["user_id"], "username": session["username"]}

# Initialize the database on import
init_db()
