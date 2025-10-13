# utils/db.py
import sqlite3
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent.parent / "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        username TEXT,
        password TEXT,
        paid INTEGER DEFAULT 0,
        free_generations_used INTEGER DEFAULT 0,
        last_generation_date TEXT DEFAULT NULL
    )
    """)
    conn.commit()
    conn.close()

def add_user(email: str, password: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, password, paid, free_generations_used) VALUES (?, ?, ?, ?)",
        (email, password, 0, 0)
    )
    conn.commit()
    conn.close()

def get_user(email: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT email, password, paid, free_generations_used, last_generation_date FROM users WHERE username=?", (email,))
    row = cur.fetchone()
    conn.close()
    return row

def set_paid(email: str, paid: bool):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET paid=? WHERE username=?", (1 if paid else 0, email))
    conn.commit()
    conn.close()

def record_generation(email: str):
    """Increment user's free generation usage."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = str(date.today())
    cur.execute(
        "UPDATE users SET free_generations_used = free_generations_used + 1, last_generation_date = ? WHERE username = ?",
        (today, email)
    )
    conn.commit()
    conn.close()
