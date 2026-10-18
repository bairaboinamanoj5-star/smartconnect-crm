import json
import os
import urllib.error
import urllib.request

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to_email, to_name, subject, body):
    """Send a plain-text email through the Brevo API.

    Returns (True, None) on success or (False, "error message") on failure.
    """
    api_key = os.environ.get("BREVO_API_KEY")
    from_email = os.environ.get("MAIL_FROM_EMAIL")
    from_name = os.environ.get("MAIL_FROM_NAME", "SmartConnect CRM")

    if not api_key or not from_email:
        return False, "Email is not configured (missing BREVO_API_KEY or MAIL_FROM_EMAIL)."

    payload = {
        "sender": {"name": from_name, "email": from_email},
        "to": [{"email": to_email, "name": to_name or to_email}],
        "subject": subject,
        "textContent": body,
    }
    request = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": api_key,
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return (200 <= response.status < 300), None
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        return False, f"Brevo error {e.code}: {detail}"
    except Exception as e:
        return False, f"Could not reach Brevo: {e}"