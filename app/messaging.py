import os
import smtplib
from email.message import EmailMessage
from .database import SessionLocal
from .models import User

# Load email configuration from environment variables
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_message(user_id: int, content: str):
    """
    Sends a message to a user via SMTP.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).one()

        # Respect the user's preferred contact method
        if user.preferred_contact_method != 'email':
            # In a real-world scenario, this would trigger a different service (e.g., WhatsApp, WebSocket push).
            print(f"✅ Simulated chat message for {user.email}: {content.splitlines()[0]}")
            return

        # Parse the subject and body from the LLM-generated content
        try:
            subject_line, body = content.split('\n\n', 1)
            subject = subject_line.replace('Subject: ', '')
        except ValueError:
            subject = "A message from your event organizer"
            body = content

        # Create the email message
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = user.email

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to {user.email}")

    except Exception as e:
        print(f"❌ Error sending email to user {user_id}: {e}")
    finally:
        db.close()