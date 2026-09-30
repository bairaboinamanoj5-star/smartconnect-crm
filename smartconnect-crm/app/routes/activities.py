from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Activity, Contact, Lead

activities_bp = Blueprint("activities", __name__, url_prefix="/activities")

ACTIVITY_TYPES = ["Call", "Email", "Meeting", "Note"]


def _visible_activities_query():
    if current_user.is_admin():
        return Activity.query
    return Activity.query.filter_by(owner_id=current_user.id)


def _visible_contacts():
    if current_user.is_admin():
        return Contact.query.order_by(Contact.first_name).all()
    return Contact.query.filter_by(owner_id=current_user.id).order_by(Contact.first_name).all()


def _visible_leads():
    if current_user.is_admin():
        return Lead.query.order_by(Lead.first_name).all()
    return Lead.query.filter_by(owner_id=current_user.id).order_by(Lead.first_name).all()


@activities_bp.route("/")
@login_required
def index():
    type_filter = request.args.get("type", "").strip()
    query = _visible_activities_query()

    if type_filter:
        query = query.filter(Activity.activity_type == type_filter)

    activities = query.order_by(Activity.activity_date.desc()).all()
    return render_template(
        "activities_list.html", activities=activities, types=ACTIVITY_TYPES, type_filter=type_filter
    )


@activities_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        contact_id = request.form.get("contact_id") or None
        lead_id = request.form.get("lead_id") or None

        activity = Activity(
            activity_type=request.form.get("activity_type", "Note"),
            subject=request.form.get("subject", "").strip(),
            description=request.form.get("description", "").strip() or None,
            activity_date=request.form.get("activity_date") or None,
            contact_id=contact_id,
            lead_id=lead_id,
            owner_id=current_user.id,
        )

        if not activity.subject:
            flash("Subject is required.", "danger")
            return redirect(url_for("activities.new"))

        if not activity.activity_date:
            from datetime import datetime
            activity.activity_date = datetime.utcnow()

        db.session.add(activity)
        db.session.commit()
        flash("Activity logged.", "success")
        return redirect(url_for("activities.index"))

    return render_template(
        "activity_form.html", activity=None, types=ACTIVITY_TYPES,
        contacts=_visible_contacts(), leads=_visible_leads()
    )


@activities_bp.route("/<int:activity_id>/edit", methods=["GET", "POST"])
@login_required
def edit(activity_id):
    activity = Activity.query.get_or_404(activity_id)

    if not current_user.is_admin() and activity.owner_id != current_user.id:
        flash("You don't have permission to edit that activity.", "danger")
        return redirect(url_for("activities.index"))

    if request.method == "POST":
        activity.activity_type = request.form.get("activity_type", "Note")
        activity.subject = request.form.get("subject", "").strip()
        activity.description = request.form.get("description", "").strip() or None
        activity.contact_id = request.form.get("contact_id") or None
        activity.lead_id = request.form.get("lead_id") or None

        if request.form.get("activity_date"):
            activity.activity_date = request.form.get("activity_date")

        if not activity.subject:
            flash("Subject is required.", "danger")
            return redirect(url_for("activities.edit", activity_id=activity.id))

        db.session.commit()
        flash("Activity updated.", "success")
        return redirect(url_for("activities.index"))

    return render_template(
        "activity_form.html", activity=activity, types=ACTIVITY_TYPES,
        contacts=_visible_contacts(), leads=_visible_leads()
    )


@activities_bp.route("/<int:activity_id>/delete", methods=["POST"])
@login_required
def delete(activity_id):
    activity = Activity.query.get_or_404(activity_id)

    if not current_user.is_admin() and activity.owner_id != current_user.id:
        flash("You don't have permission to delete that activity.", "danger")
        return redirect(url_for("activities.index"))

    db.session.delete(activity)
    db.session.commit()
    flash("Activity deleted.", "info")
    return redirect(url_for("activities.index"))