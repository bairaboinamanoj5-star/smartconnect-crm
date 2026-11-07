from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func, text

from app import db
from app.decorators import role_required
from app.models import AIUsage, Contact, EmailHistory, Lead, User

health_bp = Blueprint("health", __name__, url_prefix="/admin")


def _pct(ok, total):
    return round(100 * ok / total) if total else None


@health_bp.route("/health")
@login_required
@role_required("admin")
def index():
    now = datetime.utcnow()
    since = now - timedelta(hours=24)

    try:
        db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    ai_total = AIUsage.query.filter(AIUsage.created_at >= since).count()
    ai_failed = AIUsage.query.filter(AIUsage.created_at >= since, AIUsage.status != "ok").count()
    mail_total = EmailHistory.query.filter(EmailHistory.sent_at >= since).count()
    mail_failed = EmailHistory.query.filter(
        EmailHistory.sent_at >= since, EmailHistory.status == "failed"
    ).count()

    ai_errors = (
        AIUsage.query.outerjoin(User, User.id == AIUsage.user_id)
        .add_columns(User.first_name)
        .filter(AIUsage.status != "ok")
        .order_by(AIUsage.created_at.desc())
        .limit(25)
        .all()
    )
    mail_errors = (
        EmailHistory.query.filter(EmailHistory.status == "failed")
        .order_by(EmailHistory.sent_at.desc())
        .limit(25)
        .all()
    )

    counts = {
        "users": User.query.count(),
        "contacts": Contact.query.count(),
        "leads": Lead.query.count(),
    }

    return render_template(
        "health.html",
        db_ok=db_ok,
        ai_total=ai_total, ai_failed=ai_failed, ai_rate=_pct(ai_total - ai_failed, ai_total),
        mail_total=mail_total, mail_failed=mail_failed, mail_rate=_pct(mail_total - mail_failed, mail_total),
        ai_errors=ai_errors, mail_errors=mail_errors, counts=counts, now=now,
    )