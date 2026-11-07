from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.models import AISetting, AIUsage, User
from app.services.ai_providers import (
    PROVIDERS, AIError, encrypt_key, generate_text, get_user_setting, mask_key,
)

ai_settings_bp = Blueprint("ai_settings", __name__, url_prefix="/ai")


def _model_options():
    return {p: list(info["models"].keys()) for p, info in PROVIDERS.items()}


@ai_settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    setting = get_user_setting(current_user.id)

    if request.method == "POST":
        provider = request.form.get("provider", "gemini")
        if provider not in PROVIDERS:
            flash("Unknown AI provider.", "danger")
            return redirect(url_for("ai_settings.settings"))
        info = PROVIDERS[provider]
        email_model = request.form.get("email_model")
        action_model = request.form.get("action_model")
        if email_model not in info["models"]:
            email_model = info["default"]
        if action_model not in info["models"]:
            action_model = info["default"]

        if setting is None:
            setting = AISetting(user_id=current_user.id)
            db.session.add(setting)

        # Changing provider means the old key no longer applies.
        provider_changed = setting.provider and setting.provider != provider
        setting.provider = provider
        setting.email_model = email_model
        setting.action_model = action_model

        new_key = (request.form.get("api_key") or "").strip()
        if request.form.get("remove_key"):
            setting.api_key_enc = None
        elif new_key:
            try:
                setting.api_key_enc = encrypt_key(new_key)
            except AIError as exc:
                flash(str(exc), "danger")
                db.session.rollback()
                return redirect(url_for("ai_settings.settings"))
        elif provider_changed:
            setting.api_key_enc = None
            flash("Provider changed. Please enter an API key for the new provider.", "warning")

        db.session.commit()
        flash("AI settings saved.", "success")
        return redirect(url_for("ai_settings.settings"))

    masked = mask_key(setting.api_key_enc) if setting and setting.api_key_enc else None
    return render_template(
        "ai_settings.html",
        setting=setting,
        masked=masked,
        providers=PROVIDERS,
        model_options=_model_options(),
    )


@ai_settings_bp.route("/settings/test", methods=["POST"])
@login_required
def test_connection():
    try:
        reply = generate_text("email", "Reply with the single word OK.", timeout=15)
        flash(f"Connection works. The provider replied: {reply[:60]}", "success")
    except AIError as exc:
        flash(f"Connection test failed: {exc}", "danger")
    except Exception as exc:  # unexpected
        flash(f"Connection test failed: {exc}", "danger")
    return redirect(url_for("ai_settings.settings"))


@ai_settings_bp.route("/usage")
@login_required
def usage():
    query = AIUsage.query
    if not current_user.is_admin():
        query = query.filter(AIUsage.user_id == current_user.id)

    totals = query.with_entities(
        func.count(AIUsage.id),
        func.coalesce(func.sum(AIUsage.input_tokens), 0),
        func.coalesce(func.sum(AIUsage.output_tokens), 0),
        func.coalesce(func.sum(AIUsage.est_cost), 0),
    ).one()

    by_model = (
        query.with_entities(
            AIUsage.provider, AIUsage.model,
            func.count(AIUsage.id),
            func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0),
            func.coalesce(func.sum(AIUsage.est_cost), 0),
        )
        .group_by(AIUsage.provider, AIUsage.model)
        .order_by(func.count(AIUsage.id).desc())
        .all()
    )

    by_user = []
    if current_user.is_admin():
        by_user = (
            db.session.query(
                User.first_name, User.last_name,
                func.count(AIUsage.id),
                func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0),
                func.coalesce(func.sum(AIUsage.est_cost), 0),
            )
            .join(User, User.id == AIUsage.user_id)
            .group_by(User.id, User.first_name, User.last_name)
            .order_by(func.count(AIUsage.id).desc())
            .all()
        )

    recent = (
        query.outerjoin(User, User.id == AIUsage.user_id)
        .add_columns(User.first_name)
        .order_by(AIUsage.created_at.desc())
        .limit(50)
        .all()
    )

    return render_template(
        "ai_usage.html",
        totals=totals, by_model=by_model, by_user=by_user, recent=recent,
        providers=PROVIDERS,
    )