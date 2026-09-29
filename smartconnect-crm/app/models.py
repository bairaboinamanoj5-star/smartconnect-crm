from datetime import datetime
from flask_login import UserMixin
from app import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Enum("admin", "sales_rep", name="user_roles"), nullable=False, default="sales_rep")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
class Contact(db.Model):
    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    product_interest = db.Column(
        db.Enum("Phone", "Laptop", "Tablet", "Accessory", "Other", name="product_interest_types"),
        nullable=True,
    )
    notes = db.Column(db.Text, nullable=True)

    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    owner = db.relationship("User", backref=db.backref("contacts", lazy=True))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Contact {self.first_name} {self.last_name}>"

class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    product_interest = db.Column(
        db.Enum("Phone", "Laptop", "Tablet", "Accessory", "Other", name="lead_product_interest_types"),
        nullable=True,
    )
    stage = db.Column(
        db.Enum("New", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost", name="lead_stage_types"),
        nullable=False,
        default="New",
    )
    source = db.Column(
        db.Enum("Website", "Referral", "Walk-in", "Social Media", "Other", name="lead_source_types"),
        nullable=True,
    )
    estimated_value = db.Column(db.Numeric(10, 2), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=True)
    contact = db.relationship("Contact", backref=db.backref("leads", lazy=True))

    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    owner = db.relationship("User", backref=db.backref("leads", lazy=True))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Lead {self.first_name} {self.last_name} ({self.stage})>"