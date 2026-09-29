from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Contact

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")


def _visible_contacts_query():
    """Admins see everyone's contacts; sales reps see only their own."""
    if current_user.is_admin():
        return Contact.query
    return Contact.query.filter_by(owner_id=current_user.id)


@contacts_bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    query = _visible_contacts_query()

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Contact.first_name.ilike(like),
                Contact.last_name.ilike(like),
                Contact.email.ilike(like),
                Contact.company.ilike(like),
            )
        )

    contacts = query.order_by(Contact.created_at.desc()).all()
    return render_template("contacts_list.html", contacts=contacts, q=q)


@contacts_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        contact = Contact(
            first_name=request.form.get("first_name", "").strip(),
            last_name=request.form.get("last_name", "").strip(),
            email=request.form.get("email", "").strip().lower() or None,
            phone=request.form.get("phone", "").strip() or None,
            company=request.form.get("company", "").strip() or None,
            product_interest=request.form.get("product_interest") or None,
            notes=request.form.get("notes", "").strip() or None,
            owner_id=current_user.id,
        )

        if not contact.first_name or not contact.last_name:
            flash("First and last name are required.", "danger")
            return redirect(url_for("contacts.new"))

        db.session.add(contact)
        db.session.commit()
        flash("Contact added.", "success")
        return redirect(url_for("contacts.index"))

    return render_template("contact_form.html", contact=None)


@contacts_bp.route("/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
def edit(contact_id):
    contact = Contact.query.get_or_404(contact_id)

    if not current_user.is_admin() and contact.owner_id != current_user.id:
        flash("You don't have permission to edit that contact.", "danger")
        return redirect(url_for("contacts.index"))

    if request.method == "POST":
        contact.first_name = request.form.get("first_name", "").strip()
        contact.last_name = request.form.get("last_name", "").strip()
        contact.email = request.form.get("email", "").strip().lower() or None
        contact.phone = request.form.get("phone", "").strip() or None
        contact.company = request.form.get("company", "").strip() or None
        contact.product_interest = request.form.get("product_interest") or None
        contact.notes = request.form.get("notes", "").strip() or None

        if not contact.first_name or not contact.last_name:
            flash("First and last name are required.", "danger")
            return redirect(url_for("contacts.edit", contact_id=contact.id))

        db.session.commit()
        flash("Contact updated.", "success")
        return redirect(url_for("contacts.index"))

    return render_template("contact_form.html", contact=contact)


@contacts_bp.route("/<int:contact_id>/delete", methods=["POST"])
@login_required
def delete(contact_id):
    contact = Contact.query.get_or_404(contact_id)

    if not current_user.is_admin() and contact.owner_id != current_user.id:
        flash("You don't have permission to delete that contact.", "danger")
        return redirect(url_for("contacts.index"))

    db.session.delete(contact)
    db.session.commit()
    flash("Contact deleted.", "info")
    return redirect(url_for("contacts.index"))