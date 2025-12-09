import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
# IMPORTANT: You need to set these environment variables.
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.example.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "user@example.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "your_password")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "recipient@example.com")

def send_email_notification(source, title, link, snippet):
    """
    Sends an email notification for a new gig.
    """
    if SMTP_SERVER == "smtp.example.com":
        # Don't try to send emails with the default configuration
        return

    print(f"📧 Sending notification for: {title}")

    message = MIMEMultipart()
    message["From"] = SMTP_USER
    message["To"] = RECIPIENT_EMAIL
    message["Subject"] = f"New Gig Found on {source}: {title}"

    body = f"""
    A new potential gig has been found!

    Source: {source}
    Title: {title}
    Link: {link}

    Snippet:
    {snippet}
    """
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, RECIPIENT_EMAIL, message.as_string())
        print("✅ Notification email sent!")
    except Exception as e:
        print(f"🛑 Error sending notification email: {e}")

if __name__ == '__main__':
    # For testing the notification function
    # You would need to set the environment variables
    send_email_notification(
        source="Test Source",
        title="Test Gig Title",
        link="http://example.com",
        snippet="This is a test snippet for a gig."
    )
