from .database import SessionLocal
from .models import User
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from .config import settings

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN) if settings.TWILIO_ACCOUNT_SID else None

def _send_email_sendgrid(to_email: str, subject: str, body: str):
    """Sends an email using the SendGrid API."""
    SENDGRID_API_KEY = settings.SENDGRID_API_KEY
    SENDGRID_FROM_EMAIL = settings.SENDGRID_FROM_EMAIL
    if not SENDGRID_API_KEY or not SENDGRID_FROM_EMAIL:
        print("⚠️ SendGrid is not configured. Simulating email send.")
        print(f"✅ [SIMULATED] Email to {to_email} | Subject: {subject}")
        return

    message = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=body.replace('\n', '<br>')) # Simple conversion to HTML
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"✅ Email sent to {to_email} via SendGrid. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error sending email via SendGrid: {e}")

def _send_whatsapp_twilio(to_phone: str, body: str):
    """Sends a WhatsApp message using the Twilio API."""
    if not twilio_client or not to_phone:
        print("⚠️ Twilio is not configured or user has no phone number. Simulating WhatsApp message.")
        print(f"✅ [SIMULATED] WhatsApp to {to_phone} | Body: {body.splitlines()[0]}")
        return

    try:
        # Twilio requires the 'whatsapp:' prefix for the recipient number
        to_whatsapp_number = f'whatsapp:{to_phone}'
        message = twilio_client.messages.create(
            from_=settings.TWILIO_WHATSAPP_FROM,
            body=body,
            to=to_whatsapp_number
        )
        print(f"✅ WhatsApp message sent to {to_phone} (SID: {message.sid})")
    except Exception as e:
        print(f"❌ Error sending WhatsApp message via Twilio: {e}")

def send_message(user_id: int, content: str):
    """
    Sends a message to a user based on their preferred contact method.
    Routes to either SendGrid for email or Twilio for WhatsApp.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).one()

        # Parse the subject and body from the LLM-generated content
        try:
            subject_line, body = content.split('\n\n', 1)
            subject = subject_line.replace('Subject: ', '')
        except ValueError:
            subject = "A message from your event organizer"
            body = content # If no subject, use the whole content as body

        # Route the message based on user preference
        if user.preferred_contact_method == 'whatsapp':
            _send_whatsapp_twilio(user.phone_number, f"*{subject}*\n\n{body}")
        else: # Default to email
            _send_email_sendgrid(user.email, subject, body)

    except Exception as e:
        print(f"❌ Error sending email to user {user_id}: {e}")
    finally:
        db.close()