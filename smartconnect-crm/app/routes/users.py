from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.decorators import role_required
from app.models import Lead, User

users_bp = Blueprint("users", __name__, url_prefix="/users")

ROLES = {"admin": "Administrator", "sales_rep": "Sales Representative"}


@users_bp.route("/")
@login_required
@role_required("admin")
def index():
    lead_counts = dict(
        db.session.query(Lead.owner_id, func.count(Lead.id)).group_by(Lead.owner_id).all()
    )
    users = User.query.order_by(User.created_at.asc()).all()
    return render_template("users_list.html", users=users, roles=ROLES, lead_counts=lead_counts)


@users_bp.route("/<int:user_id>/role", methods=["POST"])
@login_required
@role_required("admin")
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")

    if new_role not in ROLES:
        flash("Unknown role.", "danger")
        return redirect(url_for("users.index"))

    if user.id == current_user.id:
        flash("You cannot change your own role. Ask another administrator.", "warning")
        return redirect(url_for("users.index"))

    if user.role == new_role:
        return redirect(url_for("users.index"))

    user.role = new_role
    db.session.commit()
    flash(f"{user.first_name} {user.last_name} is now {ROLES[new_role]}.", "success")
    return redirect(url_for("users.index"))
    