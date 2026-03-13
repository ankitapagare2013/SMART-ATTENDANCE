import pandas as pd
from database.db import get_connection
from utils.security import hash_password


def get_students(class_name="All", search_text=""):
    conn = get_connection()

    query = """
        SELECT id, full_name, username, class_name, email, roll_no, photo_path
        FROM users
        WHERE role = 'student'
    """
    params = []

    if class_name != "All":
        query += " AND class_name = ?"
        params.append(class_name)

    if search_text.strip():
        query += """
            AND (
                full_name LIKE ?
                OR roll_no LIKE ?
                OR username LIKE ?
                OR email LIKE ?
            )
        """
        search_value = f"%{search_text.strip()}%"
        params.extend([search_value, search_value, search_value, search_value])

    query += " ORDER BY full_name"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_classes():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT class_name
        FROM users
        WHERE role = 'student'
        ORDER BY class_name
    """)

    rows = cur.fetchall()
    conn.close()

    return [row[0] for row in rows]


def mark_attendance(student_id: int, status: str, marked_by: str, marked_date: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM attendance
        WHERE student_id = ? AND marked_date = ?
    """, (student_id, marked_date))

    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE attendance
            SET status = ?, marked_by = ?
            WHERE id = ?
        """, (status, marked_by, existing[0]))
    else:
        cur.execute("""
            INSERT INTO attendance (student_id, status, marked_date, marked_by)
            VALUES (?, ?, ?, ?)
        """, (student_id, status, marked_date, marked_by))

    conn.commit()
    conn.close()


def get_student_attendance(student_id: int):
    conn = get_connection()

    query = """
        SELECT status, marked_date, marked_by
        FROM attendance
        WHERE student_id = ?
        ORDER BY marked_date DESC
    """

    df = pd.read_sql_query(query, conn, params=(student_id,))
    conn.close()
    return df


def get_attendance_for_date(class_name="All", selected_date=None):
    conn = get_connection()

    if selected_date is None:
        conn.close()
        return pd.DataFrame()

    if class_name == "All":
        query = """
            SELECT
                u.id,
                u.roll_no,
                u.full_name,
                u.class_name,
                u.photo_path,
                a.status,
                a.marked_date,
                a.marked_by
            FROM users u
            LEFT JOIN attendance a
                ON u.id = a.student_id AND a.marked_date = ?
            WHERE u.role = 'student'
            ORDER BY u.full_name
        """
        df = pd.read_sql_query(query, conn, params=(selected_date,))
    else:
        query = """
            SELECT
                u.id,
                u.roll_no,
                u.full_name,
                u.class_name,
                u.photo_path,
                a.status,
                a.marked_date,
                a.marked_by
            FROM users u
            LEFT JOIN attendance a
                ON u.id = a.student_id AND a.marked_date = ?
            WHERE u.role = 'student' AND u.class_name = ?
            ORDER BY u.full_name
        """
        df = pd.read_sql_query(query, conn, params=(selected_date, class_name))

    conn.close()
    return df


def get_daily_summary(class_name="All", selected_date=None):
    df = get_attendance_for_date(class_name, selected_date)

    if df.empty:
        return {
            "total_students": 0,
            "present": 0,
            "absent": 0,
            "late": 0,
            "unmarked": 0,
        }

    status_series = df["status"].fillna("Unmarked")

    return {
        "total_students": len(df),
        "present": int((status_series == "Present").sum()),
        "absent": int((status_series == "Absent").sum()),
        "late": int((status_series == "Late").sum()),
        "unmarked": int((status_series == "Unmarked").sum()),
    }


def is_attendance_already_saved(class_name="All", selected_date=None):
    df = get_attendance_for_date(class_name, selected_date)
    if df.empty:
        return False
    return df["status"].notna().any()


def add_student(full_name, username, password, class_name, email, roll_no):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (username, password_hash, role, full_name, class_name, email, roll_no, photo_path)
            VALUES (?, ?, 'student', ?, ?, ?, ?, ?)
        """, (
            username,
            hash_password(password),
            full_name,
            class_name,
            email,
            roll_no,
            None,
        ))
        conn.commit()
        return True, "Student added successfully."
    except Exception as e:
        return False, f"Failed to add student: {e}"
    finally:
        conn.close()


def update_student(student_id, full_name, username, class_name, email, roll_no):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE users
            SET full_name = ?, username = ?, class_name = ?, email = ?, roll_no = ?
            WHERE id = ? AND role = 'student'
        """, (full_name, username, class_name, email, roll_no, student_id))
        conn.commit()
        return True, "Student updated successfully."
    except Exception as e:
        return False, f"Failed to update student: {e}"
    finally:
        conn.close()


def delete_student(student_id: int):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        cur.execute("DELETE FROM users WHERE id = ? AND role = 'student'", (student_id,))
        conn.commit()
        return True, "Student deleted successfully."
    except Exception as e:
        return False, f"Failed to delete student: {e}"
    finally:
        conn.close()


def update_student_photo(student_id: int, photo_path: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET photo_path = ?
        WHERE id = ? AND role = 'student'
    """, (photo_path, student_id))

    conn.commit()
    conn.close()


def get_student_by_id(student_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, role, full_name, class_name, email, roll_no, photo_path
        FROM users
        WHERE id = ? AND role = 'student'
    """, (student_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "role": row[2],
        "full_name": row[3],
        "class_name": row[4],
        "email": row[5],
        "roll_no": row[6],
        "photo_path": row[7],
    }


def get_student_profile_data(student_id: int):
    conn = get_connection()

    student_query = """
        SELECT id, full_name, username, class_name, email, roll_no, photo_path
        FROM users
        WHERE id = ? AND role = 'student'
    """
    student_df = pd.read_sql_query(student_query, conn, params=(student_id,))

    attendance_query = """
        SELECT status, marked_date, marked_by
        FROM attendance
        WHERE student_id = ?
        ORDER BY marked_date DESC
    """
    attendance_df = pd.read_sql_query(attendance_query, conn, params=(student_id,))

    summary_query = """
        SELECT
            COUNT(id) AS total_days,
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_days,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_days,
            SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) AS late_days
        FROM attendance
        WHERE student_id = ?
    """
    summary_df = pd.read_sql_query(summary_query, conn, params=(student_id,))
    conn.close()

    if student_df.empty:
        return None, pd.DataFrame(), None

    summary = summary_df.iloc[0].fillna(0)
    total_days = int(summary["total_days"])
    present_days = int(summary["present_days"])
    absent_days = int(summary["absent_days"])
    late_days = int(summary["late_days"])
    percentage = round((present_days / total_days) * 100, 2) if total_days > 0 else 0.0

    profile_summary = {
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "late_days": late_days,
        "attendance_percentage": percentage,
    }

    return student_df.iloc[0].to_dict(), attendance_df, profile_summary