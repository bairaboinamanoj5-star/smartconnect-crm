from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import EmailTemplate, EmailHistory, Contact
from app.services.ai_email import generate_email
from app.services.email_sender import send_email

ai_email_bp = Blueprint("ai_email", __name__, url_prefix="/ai-email")


def _visible_contacts():
    query = Contact.query.filter(Contact.email.isnot(None), Contact.email != "")
    if current_user.role != "admin":
        query = query.filter(Contact.owner_id == current_user.id)
    return query.order_by(Contact.first_name).all()


@ai_email_bp.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    subject = None
    body = None
    recipient_name = ""

    if request.method == "POST":
        recipient_name = request.form.get("recipient_name", "").strip()
        purpose = request.form.get("purpose", "").strip()
        tone = request.form.get("tone", "professional")
        product_interest = request.form.get("product_interest", "").strip()

        if not recipient_name or not purpose:
            flash("Recipient name and purpose are required.", "danger")
        else:
            try:
                subject, body = generate_email(recipient_name, purpose, tone, product_interest)
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    flash("AI service is temporarily rate-limited (free tier allows a few requests per minute). Please wait about 30 seconds and try again.", "warning")
                else:
                    flash("AI generation failed. Please try again in a moment.", "danger")

    return render_template(
        "ai_email_generate.html",
        subject=subject,
        body=body,
        recipient_name=recipient_name,
        contacts=_visible_contacts(),
    )


@ai_email_bp.route("/save-template", methods=["POST"])
@login_required
def save_template():
    name = request.form.get("name", "").strip()
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()

    if not name or not subject or not body:
        flash("A template name, subject, and body are required to save a template.", "danger")
        return redirect(url_for("ai_email.generate"))

    template = EmailTemplate(
        name=name,
        subject=subject,
        body=body,
        owner_id=current_user.id,
    )
    db.session.add(template)
    db.session.commit()
    flash("Saved as an email template!", "success")
    return redirect(url_for("email_templates.index"))


@ai_email_bp.route("/send", methods=["POST"])
@login_required
def send():
    recipient_email = request.form.get("recipient_email", "").strip()
    recipient_name = request.form.get("recipient_name", "").strip()
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()
    contact_id = request.form.get("contact_id", "").strip()

    if not recipient_email or "@" not in recipient_email or not subject or not body:
        flash("A valid recipient email, a subject, and a body are required to send.", "danger")
        return render_template(
            "ai_email_generate.html",
            subject=subject,
            body=body,
            recipient_name=recipient_name,
            contacts=_visible_contacts(),
        )

    linked_contact_id = None
    if contact_id.isdigit():
        contact = Contact.query.get(int(contact_id))
        if contact and (current_user.role == "admin" or contact.owner_id == current_user.id):
            linked_contact_id = contact.id

    ok, error = send_email(recipient_email, recipient_name, subject, body)

    record = EmailHistory(
        recipient_email=recipient_email,
        recipient_name=recipient_name or None,
        subject=subject,
        body=body,
        status="sent" if ok else "failed",
        error_message=None if ok else error,
        owner_id=current_user.id,
        contact_id=linked_contact_id,
    )
    db.session.add(record)
    db.session.commit()

    if ok:
        flash(f"Email sent to {recipient_email}.", "success")
        return redirect(url_for("ai_email.history"))

    flash("The email could not be sent. The failure was saved in Email History.", "danger")
    return render_template(
        "ai_email_generate.html",
        subject=subject,
        body=body,
        recipient_name=recipient_name,
        contacts=_visible_contacts(),
    )


@ai_email_bp.route("/history")
@login_required
def history():
    query = EmailHistory.query
    if current_user.role != "admin":
        query = query.filter(EmailHistory.owner_id == current_user.id)
    emails = query.order_by(EmailHistory.sent_at.desc()).all()
    return render_template("email_history.html", emails=emails)