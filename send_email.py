import smtplib
import SHP_config
import os
import re
import email
import json
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
def send_failure_alert(subject, message):
    """Send an alert email if the script fails."""
    alert_email = os.getenv('EMAIL_SENDER')
    alert_password = os.getenv('EMAIL_SENDER_PASSWORD')
    ALERT_RECEIVER = os.getenv('ALERT_RECEIVER_EMAIL')
    if not alert_email or not alert_password or not ALERT_RECEIVER:
        print("Missing alert email credentials or receiver.")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = alert_email
        msg["To"] = ALERT_RECEIVER
        msg["Subject"] = subject

        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(alert_email, alert_password)
            server.sendmail(alert_email, ALERT_RECEIVER, msg.as_string())

    except Exception as e:
        pass
        #print(f"Failed to send alert email: {e}")
