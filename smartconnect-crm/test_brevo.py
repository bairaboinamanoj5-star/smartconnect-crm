from dotenv import load_dotenv
import os

load_dotenv()

from app.services.email_sender import send_email

to = os.environ.get("MAIL_FROM_EMAIL")
ok, error = send_email(
    to,
    "Test",
    "SmartConnect CRM test email",
    "If you can read this, Brevo sending works.",
)
print("Sent!" if ok else f"Failed: {error}")