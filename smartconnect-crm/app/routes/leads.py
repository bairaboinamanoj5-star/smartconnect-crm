from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Lead

leads_bp = Blueprint("leads", __name__, url_prefix="/leads")

STAGES = ["New", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost"]
SOURCES = ["Website", "Referral", "Walk-in", "Social Media", "Other"]
PRODUCT_INTERESTS = ["Phone", "Laptop", "Tablet", "Accessory", "Other"]


def _visible_leads_query():
    if current_user.is_admin():
        return Lead.query
    return Lead.query.filter_by(owner_id=current_user.id)


@leads_bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    stage_filter = request.args.get("stage", "").strip()

    query = _visible_leads_query()

    if stage_filter:
        query = query.filter(Lead.stage == stage_filter)

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Lead.first_name.ilike(like),
                Lead.last_name.ilike(like),
                Lead.email.ilike(like),
                Lead.company.ilike(like),
            )
        )

    leads = query.order_by(Lead.created_at.desc()).all()
    return render_template("leads_list.html", leads=leads, q=q, stage_filter=stage_filter, stages=STAGES)


@leads_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        estimated_value = request.form.get("estimated_value", "").strip()
        lead = Lead(
            first_name=request.form.get("first_name", "").strip(),
            last_name=request.form.get("last_name", "").strip(),
            email=request.form.get("email", "").strip().lower() or None,
            phone=request.form.get("phone", "").strip() or None,
            company=request.form.get("company", "").strip() or None,
            product_interest=request.form.get("product_interest") or None,
            stage=request.form.get("stage") or "New",
            source=request.form.get("source") or None,
            estimated_value=estimated_value or None,
            notes=request.form.get("notes", "").strip() or None,
            owner_id=current_user.id,
        )

        if not lead.first_name or not lead.last_name:
            flash("First and last name are required.", "danger")
            return redirect(url_for("leads.new"))

        db.session.add(lead)
        db.session.commit()
        flash("Lead added.", "success")
        return redirect(url_for("leads.index"))

    return render_template(
        "lead_form.html", lead=None, stages=STAGES, sources=SOURCES, product_interests=PRODUCT_INTERESTS
    )


@leads_bp.route("/<int:lead_id>/edit", methods=["GET", "POST"])
@login_required
def edit(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if not current_user.is_admin() and lead.owner_id != current_user.id:
        flash("You don't have permission to edit that lead.", "danger")
        return redirect(url_for("leads.index"))

    if request.method == "POST":
        estimated_value = request.form.get("estimated_value", "").strip()
        lead.first_name = request.form.get("first_name", "").strip()
        lead.last_name = request.form.get("last_name", "").strip()
        lead.email = request.form.get("email", "").strip().lower() or None
        lead.phone = request.form.get("phone", "").strip() or None
        lead.company = request.form.get("company", "").strip() or None
        lead.product_interest = request.form.get("product_interest") or None
        lead.stage = request.form.get("stage") or "New"
        lead.source = request.form.get("source") or None
        lead.estimated_value = estimated_value or None
        lead.notes = request.form.get("notes", "").strip() or None

        if not lead.first_name or not lead.last_name:
            flash("First and last name are required.", "danger")
            return redirect(url_for("leads.edit", lead_id=lead.id))

        db.session.commit()
        flash("Lead updated.", "success")
        return redirect(url_for("leads.index"))

    return render_template(
        "lead_form.html", lead=lead, stages=STAGES, sources=SOURCES, product_interests=PRODUCT_INTERESTS
    )


@leads_bp.route("/<int:lead_id>/delete", methods=["POST"])
@login_required
def delete(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if not current_user.is_admin() and lead.owner_id != current_user.id:
        flash("You don't have permission to delete that lead.", "danger")
        return redirect(url_for("leads.index"))

    db.session.delete(lead)
    db.session.commit()
    flash("Lead deleted.", "info")
    return redirect(url_for("leads.index"))