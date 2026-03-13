import smtplib
from email.message import EmailMessage

sender_email = "YOUR_SENDER_GMAIL@gmail.com"
app_password = "YOUR_16_CHAR_APP_PASSWORD"
receiver_email = "YOUR_OTHER_EMAIL@gmail.com"

msg = EmailMessage()
msg["Subject"] = "Test Email from Smart Attendance"
msg["From"] = sender_email
msg["To"] = receiver_email
msg.set_content("This is a test email sent from Python.")

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)

    print("Email sent successfully.")
except Exception as e:
    print("Error:", e)