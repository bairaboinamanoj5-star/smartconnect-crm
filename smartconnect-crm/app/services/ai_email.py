from app.services.ai_providers import generate_text


def generate_email(recipient_name, purpose, tone="professional", product_interest=None):
    prompt = f"""You are an assistant helping a sales rep at an electronics retail company write a short sales/follow-up email.

Recipient name: {recipient_name}
Purpose of the email: {purpose}
Tone: {tone}
"""
    if product_interest:
        prompt += f"Product interest: {product_interest}\n"

    prompt += """
Write a subject line and a short email body (3-5 sentences).
Respond ONLY in this exact format, nothing else:

SUBJECT: <subject line here>
BODY:
<email body here>
"""

    text = generate_text("email", prompt, timeout=20)

    if "SUBJECT:" in text and "BODY:" in text:
        subject = text.split("SUBJECT:")[1].split("BODY:")[0].strip()
        body = text.split("BODY:")[1].strip()
    else:
        subject = "Following up"
        body = text

    return subject, body