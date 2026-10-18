import csv
import io
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from app import db
from app.models import Contact, Lead

data_io_bp = Blueprint("data_io", __name__, url_prefix="/data")

PRODUCT_INTERESTS = ["Phone", "Laptop", "Tablet", "Accessory", "Other"]
STAGES = ["New", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost"]
SOURCES = ["Website", "Referral", "Walk-in", "Social Media", "Other"]

CONTACT_COLUMNS = ["first_name", "last_name", "email", "phone", "company", "product_interest", "notes"]
LEAD_COLUMNS = ["first_name", "last_name", "email", "phone", "company", "product_interest",
                "stage", "source", "estimated_value", "notes"]

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000


def _match(value, options):
    wanted = (value or "").strip().lower()
    for option in options:
        if option.lower() == wanted:
            return option
    return None


def _safe(value):
    """Stop spreadsheet apps from running cells that start with a formula character."""
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@"):
        return "'" + text
    return text


def _visible(model):
    query = model.query
    if current_user.role != "admin":
        query = query.filter(model.owner_id == current_user.id)
    return query


def _csv_response(filename, columns, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _read_csv(upload, required):
    if upload is None or not upload.filename:
        return None, "Please choose a CSV file first."
    raw = upload.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        return None, "That file is too large (2 MB limit)."
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "Could not read the file. Please save it as a UTF-8 CSV."

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return None, "The file is empty."
    reader.fieldnames = [(name or "").strip().lower() for name in reader.fieldnames]
    missing = [col for col in required if col not in reader.fieldnames]
    if missing:
        return None, "Missing required column(s): " + ", ".join(missing)

    rows = []
    for row in reader:
        rows.append(row)
        if len(rows) > MAX_ROWS:
            return None, f"Too many rows (limit is {MAX_ROWS})."
    return rows, None


def _clean(row, key, limit=None):
    value = (row.get(key) or "").strip()
    if limit:
        value = value[:limit]
    return value or None


@data_io_bp.route("/")
@login_required
def index():
    return render_template("data_io.html")


@data_io_bp.route("/export/contacts")
@login_required
def export_contacts():
    contacts = _visible(Contact).order_by(Contact.id).all()
    rows = [
        [_safe(c.first_name), _safe(c.last_name), _safe(c.email), _safe(c.phone),
         _safe(c.company), _safe(c.product_interest), _safe(c.notes)]
        for c in contacts
    ]
    return _csv_response("contacts.csv", CONTACT_COLUMNS, rows)


@data_io_bp.route("/export/leads")
@login_required
def export_leads():
    leads = _visible(Lead).order_by(Lead.id).all()
    rows = [
        [_safe(l.first_name), _safe(l.last_name), _safe(l.email), _safe(l.phone),
         _safe(l.company), _safe(l.product_interest), _safe(l.stage), _safe(l.source),
         l.estimated_value if l.estimated_value is not None else "", _safe(l.notes)]
        for l in leads
    ]
    return _csv_response("leads.csv", LEAD_COLUMNS, rows)


@data_io_bp.route("/template/<kind>")
@login_required
def template(kind):
    if kind == "contacts":
        sample = ["Jane", "Doe", "jane@example.com", "555-0100", "Acme Retail", "Laptop", "Met at store"]
        return _csv_response("contacts_template.csv", CONTACT_COLUMNS, [sample])
    if kind == "leads":
        sample = ["Jane", "Doe", "jane@example.com", "555-0100", "Acme Retail", "Laptop",
                  "New", "Website", "1200.00", "Interested in gaming laptops"]
        return _csv_response("leads_template.csv", LEAD_COLUMNS, [sample])
    return redirect(url_for("data_io.index"))


@data_io_bp.route("/import/contacts", methods=["POST"])
@login_required
def import_contacts():
    rows, error = _read_csv(request.files.get("file"), ["first_name", "last_name"])
    if error:
        flash(error, "danger")
        return redirect(url_for("data_io.index"))

    existing = {
        c.email.lower()
        for c in Contact.query.filter_by(owner_id=current_user.id)
        if c.email
    }
    imported = skipped = 0

    for row in rows:
        first = _clean(row, "first_name", 50)
        last = _clean(row, "last_name", 50)
        email = _clean(row, "email", 120)

        if not first or not last or (email and "@" not in email):
            skipped += 1
            continue
        if email and email.lower() in existing:
            skipped += 1
            continue

        db.session.add(Contact(
            first_name=first,
            last_name=last,
            email=email,
            phone=_clean(row, "phone", 20),
            company=_clean(row, "company", 100),
            product_interest=_match(row.get("product_interest"), PRODUCT_INTERESTS),
            notes=_clean(row, "notes"),
            owner_id=current_user.id,
        ))
        imported += 1
        if email:
            existing.add(email.lower())

    db.session.commit()
    flash(
        f"Imported {imported} contact(s). Skipped {skipped} row(s) (missing name, invalid email, or duplicate email).",
        "success" if imported else "warning",
    )
    return redirect(url_for("contacts.index"))


@data_io_bp.route("/import/leads", methods=["POST"])
@login_required
def import_leads():
    rows, error = _read_csv(request.files.get("file"), ["first_name", "last_name"])
    if error:
        flash(error, "danger")
        return redirect(url_for("data_io.index"))

    existing = {
        ((l.first_name or "").lower(), (l.last_name or "").lower(), (l.email or "").lower())
        for l in Lead.query.filter_by(owner_id=current_user.id)
    }
    imported = skipped = 0

    for row in rows:
        first = _clean(row, "first_name", 50)
        last = _clean(row, "last_name", 50)
        email = _clean(row, "email", 120)

        if not first or not last or (email and "@" not in email):
            skipped += 1
            continue
        key = (first.lower(), last.lower(), (email or "").lower())
        if key in existing:
            skipped += 1
            continue

        value = None
        raw_value = (row.get("estimated_value") or "").replace("$", "").replace(",", "").strip()
        if raw_value:
            try:
                parsed = Decimal(raw_value)
                if 0 <= parsed < Decimal("100000000"):
                    value = parsed
            except InvalidOperation:
                value = None

        db.session.add(Lead(
            first_name=first,
            last_name=last,
            email=email,
            phone=_clean(row, "phone", 20),
            company=_clean(row, "company", 100),
            product_interest=_match(row.get("product_interest"), PRODUCT_INTERESTS),
            stage=_match(row.get("stage"), STAGES) or "New",
            source=_match(row.get("source"), SOURCES),
            estimated_value=value,
            notes=_clean(row, "notes"),
            owner_id=current_user.id,
        ))
        imported += 1
        existing.add(key)

    db.session.commit()
    flash(
        f"Imported {imported} lead(s). Skipped {skipped} row(s) (missing name, invalid email, or duplicate).",
        "success" if imported else "warning",
    )
    return redirect(url_for("leads.index"))