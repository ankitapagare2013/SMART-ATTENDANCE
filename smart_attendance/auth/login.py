from database.db import get_connection
from utils.security import hash_password


def authenticate(username: str, password: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, role, full_name, class_name, password_hash
        FROM users
        WHERE username = ?
    """, (username,))

    row = cur.fetchone()
    conn.close()

    if row and row[5] == hash_password(password):
        return {
            "id": row[0],
            "username": row[1],
            "role": row[2],
            "full_name": row[3],
            "class_name": row[4],
        }

    return None