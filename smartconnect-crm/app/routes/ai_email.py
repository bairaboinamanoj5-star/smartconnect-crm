from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import EmailTemplate
from app.services.ai_email import generate_email

ai_email_bp = Blueprint("ai_email", __name__, url_prefix="/ai-email")


@ai_email_bp.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    subject = None
    body = None

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
                flash(f"AI generation failed: {e}", "danger")

    return render_template("ai_email_generate.html", subject=subject, body=body)


@ai_email_bp.route("/save-template", methods=["POST"])
@login_required
def save_template():
    name = request.form.get("name", "").strip()
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()

    if not name or not subject or not body:
        flash("Name, subject, and body are required to save a template.", "danger")
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