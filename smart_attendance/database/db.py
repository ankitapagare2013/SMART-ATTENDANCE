import sqlite3
from pathlib import Path
from utils.security import hash_password

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "attendance.db"


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL,
            class_name TEXT,
            email TEXT,
            roll_no TEXT UNIQUE,
            photo_path TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            marked_date TEXT NOT NULL,
            marked_by TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def seed_demo_data():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]

    if count == 0:
        users = [
            ("admin", hash_password("admin123"), "admin", "System Admin", "ADMIN", "admin@example.com", "ADMIN-001", None),
            ("john", hash_password("john123"), "student", "John Carter", "ME-A", "john@example.com", "MEA-001", None),
            ("sara", hash_password("sara123"), "student", "Sara Khan", "ME-A", "sara@example.com", "MEA-002", None),
            ("alex", hash_password("alex123"), "student", "Alex Roy", "ME-B", "alex@example.com", "MEB-001", None),
            ("priya", hash_password("priya123"), "student", "Priya Sharma", "ME-B", "priya@example.com", "MEB-002", None),
        ]

        cur.executemany("""
            INSERT INTO users (
                username, password_hash, role, full_name, class_name, email, roll_no, photo_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, users)

    conn.commit()
    conn.close()