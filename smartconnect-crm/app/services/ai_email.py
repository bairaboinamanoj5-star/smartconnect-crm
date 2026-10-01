import google.generativeai as genai
from flask import current_app


def generate_email(recipient_name, purpose, tone="professional", product_interest=None):
    api_key = current_app.config.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-flash-latest")

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

    response = model.generate_content(prompt)
    text = response.text.strip()

    if "SUBJECT:" in text and "BODY:" in text:
        subject = text.split("SUBJECT:")[1].split("BODY:")[0].strip()
        body = text.split("BODY:")[1].strip()
    else:
        subject = "Following up"
        body = text

    return subject, body