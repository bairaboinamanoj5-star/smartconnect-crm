from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models import Contact, Lead, Activity, User
from app.services.lead_ai import score_lead

dashboard_bp = Blueprint("dashboard", __name__)

STAGES = ["New", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost"]
SOURCES = ["Website", "Referral", "Walk-in", "Social Media", "Other"]


def _scoped(model):
    q = model.query
    if current_user.role != "admin":
        q = q.filter(model.owner_id == current_user.id)
    return q


def _pct(part, whole):
    return round(part / whole * 100, 1) if whole else 0.0


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

    # ---- Analytics ----
    leads = _scoped(Lead).all()
    total = len(leads)
    won = sum(1 for l in leads if l.stage == "Won")
    lost = sum(1 for l in leads if l.stage == "Lost")
    conversion_rate = _pct(won, total)          # won / all leads
    win_rate = _pct(won, won + lost)            # won / closed leads
    won_value = float(sum((l.estimated_value or 0) for l in leads if l.stage == "Won"))
    pipeline_value = float(sum(
        (l.estimated_value or 0) for l in leads if l.stage not in ("Won", "Lost")
    ))

    # Lead scoring counts (open leads only)
    last_map = {}
    if leads:
        act_rows = (
            db.session.query(Activity.lead_id, func.max(Activity.activity_date))
            .filter(Activity.lead_id.in_([l.id for l in leads]))
            .group_by(Activity.lead_id)
            .all()
        )
        last_map = dict(act_rows)
    score_counts = {"Hot": 0, "Warm": 0, "Cold": 0}
    for l in leads:
        sc = score_lead(l, last_map.get(l.id))
        if sc:
            score_counts[sc["label"]] += 1

    # Leads by source
    src = {}
    for l in leads:
        name = l.source or "Unknown"
        entry = src.setdefault(name, {"count": 0, "won": 0})
        entry["count"] += 1
        if l.stage == "Won":
            entry["won"] += 1
    ordered = [s for s in SOURCES if s in src] + [s for s in src if s not in SOURCES]
    source_rows = [
        (s, src[s]["count"], src[s]["won"], _pct(src[s]["won"], src[s]["count"]))
        for s in ordered
    ]
    max_source = max([r[1] for r in source_rows] + [1])

    # Sales performance per rep
    if current_user.role == "admin":
        users = {u.id: u for u in User.query.all()}
    else:
        users = {current_user.id: current_user}
    stats = {}
    for l in leads:
        s = stats.setdefault(l.owner_id, {"leads": 0, "won": 0, "lost": 0, "won_value": 0.0})
        s["leads"] += 1
        if l.stage == "Won":
            s["won"] += 1
            s["won_value"] += float(l.estimated_value or 0)
        elif l.stage == "Lost":
            s["lost"] += 1
    rep_rows = []
    for uid, u in users.items():
        s = stats.get(uid, {"leads": 0, "won": 0, "lost": 0, "won_value": 0.0})
        if s["leads"] or u.role != "admin":
            rep_rows.append({
                "name": u.first_name,
                "role": u.role,
                "leads": s["leads"],
                "won": s["won"],
                "win_rate": _pct(s["won"], s["won"] + s["lost"]),
                "won_value": s["won_value"],
            })
    rep_rows.sort(key=lambda r: r["won_value"], reverse=True)

    return render_template(
        "dashboard.html",
        user=current_user,
        contact_count=contact_count,
        lead_count=lead_count,
        won_count=won_count,
        activity_count=activity_count,
        stage_counts=stage_counts,
        max_count=max_count,
        conversion_rate=conversion_rate,
        win_rate=win_rate,
        won_value=won_value,
        pipeline_value=pipeline_value,
        score_counts=score_counts,
        source_rows=source_rows,
        max_source=max_source,
        rep_rows=rep_rows,
    )