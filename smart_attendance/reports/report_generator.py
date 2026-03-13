import io
import pandas as pd
from database.db import get_connection


def generate_attendance_report(class_name="All", selected_date=None):
    conn = get_connection()

    if selected_date:
        if class_name == "All":
            query = """
                SELECT
                    u.id,
                    u.roll_no,
                    u.full_name,
                    u.username,
                    u.class_name,
                    u.email,
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
                    u.username,
                    u.class_name,
                    u.email,
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
    else:
        if class_name == "All":
            query = """
                SELECT
                    u.id,
                    u.roll_no,
                    u.full_name,
                    u.username,
                    u.class_name,
                    u.email,
                    a.status,
                    a.marked_date,
                    a.marked_by
                FROM users u
                LEFT JOIN attendance a
                    ON u.id = a.student_id
                WHERE u.role = 'student'
                ORDER BY u.full_name, a.marked_date DESC
            """
            df = pd.read_sql_query(query, conn)
        else:
            query = """
                SELECT
                    u.id,
                    u.roll_no,
                    u.full_name,
                    u.username,
                    u.class_name,
                    u.email,
                    a.status,
                    a.marked_date,
                    a.marked_by
                FROM users u
                LEFT JOIN attendance a
                    ON u.id = a.student_id
                WHERE u.role = 'student' AND u.class_name = ?
                ORDER BY u.full_name, a.marked_date DESC
            """
            df = pd.read_sql_query(query, conn, params=(class_name,))

    conn.close()
    return df


def calculate_attendance_percentage():
    conn = get_connection()

    query = """
        SELECT
            u.roll_no,
            u.full_name,
            u.username,
            u.class_name,
            u.email,
            COUNT(a.id) AS total_days,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_days,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_days,
            SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) AS late_days
        FROM users u
        LEFT JOIN attendance a
            ON u.id = a.student_id
        WHERE u.role = 'student'
        GROUP BY u.id, u.roll_no, u.full_name, u.username, u.class_name, u.email
        ORDER BY u.full_name
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return df

    df["total_days"] = df["total_days"].fillna(0).astype(int)
    df["present_days"] = df["present_days"].fillna(0).astype(int)
    df["absent_days"] = df["absent_days"].fillna(0).astype(int)
    df["late_days"] = df["late_days"].fillna(0).astype(int)

    def percentage(row):
        if row["total_days"] == 0:
            return 0.0
        return round((row["present_days"] / row["total_days"]) * 100, 2)

    df["attendance_percentage"] = df.apply(percentage, axis=1)
    return df


def get_monthly_attendance_report(class_name="All", year=None, month=None):
    conn = get_connection()

    if year is None or month is None:
        conn.close()
        return pd.DataFrame()

    month_str = f"{year:04d}-{month:02d}"

    if class_name == "All":
        query = """
            SELECT
                u.id,
                u.roll_no,
                u.full_name,
                u.class_name,
                u.email,
                SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_days,
                SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_days,
                SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) AS late_days,
                COUNT(a.id) AS total_marked_days
            FROM users u
            LEFT JOIN attendance a
                ON u.id = a.student_id
                AND substr(a.marked_date, 1, 7) = ?
            WHERE u.role = 'student'
            GROUP BY u.id, u.roll_no, u.full_name, u.class_name, u.email
            ORDER BY u.full_name
        """
        df = pd.read_sql_query(query, conn, params=(month_str,))
    else:
        query = """
            SELECT
                u.id,
                u.roll_no,
                u.full_name,
                u.class_name,
                u.email,
                SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_days,
                SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_days,
                SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) AS late_days,
                COUNT(a.id) AS total_marked_days
            FROM users u
            LEFT JOIN attendance a
                ON u.id = a.student_id
                AND substr(a.marked_date, 1, 7) = ?
            WHERE u.role = 'student' AND u.class_name = ?
            GROUP BY u.id, u.roll_no, u.full_name, u.class_name, u.email
            ORDER BY u.full_name
        """
        df = pd.read_sql_query(query, conn, params=(month_str, class_name))

    conn.close()

    if df.empty:
        return df

    for col in ["present_days", "absent_days", "late_days", "total_marked_days"]:
        df[col] = df[col].fillna(0).astype(int)

    def percentage(row):
        if row["total_marked_days"] == 0:
            return 0.0
        return round((row["present_days"] / row["total_marked_days"]) * 100, 2)

    df["monthly_attendance_percentage"] = df.apply(percentage, axis=1)
    return df


def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def convert_df_to_excel(df):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Attendance Report")

    return output.getvalue()