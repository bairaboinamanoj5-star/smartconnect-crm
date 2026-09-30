from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import EmailTemplate

email_templates_bp = Blueprint("email_templates", __name__, url_prefix="/email-templates")


@email_templates_bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    query = EmailTemplate.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                EmailTemplate.name.ilike(like),
                EmailTemplate.subject.ilike(like),
            )
        )

    templates = query.order_by(EmailTemplate.created_at.desc()).all()
    return render_template("email_templates_list.html", templates=templates, q=q)


@email_templates_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        template = EmailTemplate(
            name=request.form.get("name", "").strip(),
            subject=request.form.get("subject", "").strip(),
            body=request.form.get("body", "").strip(),
            owner_id=current_user.id,
        )

        if not template.name or not template.subject or not template.body:
            flash("Name, subject, and body are all required.", "danger")
            return redirect(url_for("email_templates.new"))

        db.session.add(template)
        db.session.commit()
        flash("Email template created.", "success")
        return redirect(url_for("email_templates.index"))

    return render_template("email_template_form.html", template=None)


@email_templates_bp.route("/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
def edit(template_id):
    template = EmailTemplate.query.get_or_404(template_id)

    if not current_user.is_admin() and template.owner_id != current_user.id:
        flash("You don't have permission to edit that template.", "danger")
        return redirect(url_for("email_templates.index"))

    if request.method == "POST":
        template.name = request.form.get("name", "").strip()
        template.subject = request.form.get("subject", "").strip()
        template.body = request.form.get("body", "").strip()

        if not template.name or not template.subject or not template.body:
            flash("Name, subject, and body are all required.", "danger")
            return redirect(url_for("email_templates.edit", template_id=template.id))

        db.session.commit()
        flash("Email template updated.", "success")
        return redirect(url_for("email_templates.index"))

    return render_template("email_template_form.html", template=template)


@email_templates_bp.route("/<int:template_id>/delete", methods=["POST"])
@login_required
def delete(template_id):
    template = EmailTemplate.query.get_or_404(template_id)

    if not current_user.is_admin() and template.owner_id != current_user.id:
        flash("You don't have permission to delete that template.", "danger")
        return redirect(url_for("email_templates.index"))

    db.session.delete(template)
    db.session.commit()
    flash("Email template deleted.", "info")
    return redirect(url_for("email_templates.index"))