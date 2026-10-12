from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models import Contact, Lead, Activity

dashboard_bp = Blueprint("dashboard", __name__)

STAGES = ["New", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost"]


def _scoped(model):
    q = model.query
    if current_user.role != "admin":
        q = q.filter(model.owner_id == current_user.id)
    return q


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    contact_count = _scoped(Contact).count()
    lead_count = _scoped(Lead).count()
    activity_count = _scoped(Activity).count()
    won_count = _scoped(Lead).filter(Lead.stage == "Won").count()

    rows = (
        _scoped(Lead)
        .with_entities(Lead.stage, func.count(Lead.id))
        .group_by(Lead.stage)
        .all()
    )
    by_stage = {stage: count for stage, count in rows}
    stage_counts = [(s, by_stage.get(s, 0)) for s in STAGES]
    max_count = max([c for _, c in stage_counts] + [1])

    return render_template(
        "dashboard.html",
        user=current_user,
        contact_count=contact_count,
        lead_count=lead_count,
        won_count=won_count,
        activity_count=activity_count,
        stage_counts=stage_counts,
        max_count=max_count,
    )