import smtplib
from email.message import EmailMessage
from io import BytesIO
import pandas as pd


def create_excel_attachment(df: pd.DataFrame, filename: str) -> tuple[bytes, str]:
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")

    return output.getvalue(), filename


def send_email_with_attachment(
    sender_email: str,
    app_password: str,
    receiver_email: str,
    subject: str,
    body: str,
    attachment_bytes: bytes | None = None,
    attachment_filename: str | None = None,
):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content(body)

    if attachment_bytes is not None and attachment_filename is not None:
        msg.add_attachment(
            attachment_bytes,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=attachment_filename,
        )

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)


def send_monthly_reports_to_students(
    sender_email: str,
    app_password: str,
    monthly_df: pd.DataFrame,
    year: int,
    month: int,
):
    sent = 0
    failed: list[str] = []

    if monthly_df.empty:
        return sent, ["No monthly data available."]

    for _, row in monthly_df.iterrows():
        receiver_email = str(row.get("email", "")).strip()

        if not receiver_email or receiver_email.lower() == "nan":
            failed.append(f"{row['full_name']} - missing email")
            continue

        student_df = pd.DataFrame([row])
        attachment_bytes, filename = create_excel_attachment(
            student_df,
            f"monthly_report_{row['roll_no']}_{year}_{month:02d}.xlsx"
        )

        subject = f"Monthly Attendance Report - {year}-{month:02d}"
        body = f"""
Dear {row['full_name']},

Please find attached your monthly attendance report for {year}-{month:02d}.

Summary:
- Roll Number: {row['roll_no']}
- Class: {row['class_name']}
- Present Days: {row['present_days']}
- Absent Days: {row['absent_days']}
- Late Days: {row['late_days']}
- Attendance Percentage: {row['monthly_attendance_percentage']}%

Regards,
Smart Attendance System
""".strip()

        try:
            send_email_with_attachment(
                sender_email=sender_email,
                app_password=app_password,
                receiver_email=receiver_email,
                subject=subject,
                body=body,
                attachment_bytes=attachment_bytes,
                attachment_filename=filename,
            )
            sent += 1
        except Exception as e:
            failed.append(f"{row['full_name']} - {e}")

    return sent, failed


def send_low_attendance_warnings(
    sender_email: str,
    app_password: str,
    low_df: pd.DataFrame,
):
    sent = 0
    failed: list[str] = []

    if low_df.empty:
        return sent, ["No low attendance students found."]

    for _, row in low_df.iterrows():
        receiver_email = str(row.get("email", "")).strip()

        if not receiver_email or receiver_email.lower() == "nan":
            failed.append(f"{row['full_name']} - missing email")
            continue

        student_df = pd.DataFrame([row])
        attachment_bytes, filename = create_excel_attachment(
            student_df,
            f"low_attendance_warning_{row['roll_no']}.xlsx"
        )

        subject = "Attendance Warning - Low Attendance Detected"
        body = f"""
Dear {row['full_name']},

This is a warning regarding your attendance.

Your current attendance percentage is {row['attendance_percentage']}%, which is below the required 75%.

Summary:
- Roll Number: {row['roll_no']}
- Class: {row['class_name']}
- Present Days: {row['present_days']}
- Absent Days: {row['absent_days']}
- Late Days: {row['late_days']}

Please improve your attendance immediately to avoid being marked as a defaulter.

Regards,
Smart Attendance System
""".strip()

        try:
            send_email_with_attachment(
                sender_email=sender_email,
                app_password=app_password,
                receiver_email=receiver_email,
                subject=subject,
                body=body,
                attachment_bytes=attachment_bytes,
                attachment_filename=filename,
            )
            sent += 1
        except Exception as e:
            failed.append(f"{row['full_name']} - {e}")

    return sent, failed