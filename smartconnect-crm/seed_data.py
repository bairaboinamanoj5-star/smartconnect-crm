import random
from datetime import datetime, timedelta

from faker import Faker

from app import create_app, db, bcrypt
from app.models import User, Contact, Lead, Activity

app = create_app()
fake = Faker()

PRODUCT_INTERESTS = ["Phone", "Laptop", "Tablet", "Accessory", "Other"]
LEAD_STAGES = ["New", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost"]
LEAD_SOURCES = ["Website", "Referral", "Walk-in", "Social Media", "Other"]
ACTIVITY_TYPES = ["Call", "Email", "Meeting", "Note"]

ELECTRONICS_COMPANIES = [
    "TechHive Electronics", "ByteMart", "GadgetWorks", "CircuitCity Retail",
    "NextGen Devices", "PixelPoint Store", "MobileEdge", "SmartBuy Electronics",
    "CoreTech Solutions", "Quantum Gadgets",
]


def get_or_create_sales_reps():
    """Ensure we have a few sales rep users to own the seeded data."""
    reps = User.query.filter_by(role="sales_rep").all()

    needed = 3 - len(reps)
    for i in range(max(needed, 0)):
        email = f"seed.rep{i+1}@smartconnect.test"
        existing = User.query.filter_by(email=email).first()
        if existing:
            reps.append(existing)
            continue

        rep = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            password_hash=bcrypt.generate_password_hash("password123").decode("utf-8"),
            role="sales_rep",
        )
        db.session.add(rep)
        reps.append(rep)

    db.session.commit()
    return reps


def seed():
    if Contact.query.count() > 0:
        print("Contacts already exist — skipping seed to avoid duplicates.")
        print("If you want to re-seed, clear the contacts/leads/activities tables first.")
        return

    reps = get_or_create_sales_reps()
    print(f"Using {len(reps)} sales rep(s) as data owners.")

    contacts = []
    for _ in range(25):
        contact = Contact(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],
            company=random.choice(ELECTRONICS_COMPANIES),
            product_interest=random.choice(PRODUCT_INTERESTS),
            notes=fake.sentence(nb_words=10),
            owner_id=random.choice(reps).id,
        )
        db.session.add(contact)
        contacts.append(contact)

    db.session.commit()
    print(f"Created {len(contacts)} contacts.")

    leads = []
    for _ in range(20):
        lead = Lead(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],
            company=random.choice(ELECTRONICS_COMPANIES),
            product_interest=random.choice(PRODUCT_INTERESTS),
            stage=random.choice(LEAD_STAGES),
            source=random.choice(LEAD_SOURCES),
            estimated_value=round(random.uniform(150, 2500), 2),
            notes=fake.sentence(nb_words=10),
            owner_id=random.choice(reps).id,
        )
        db.session.add(lead)
        leads.append(lead)

    db.session.commit()
    print(f"Created {len(leads)} leads.")

    activities = []
    for _ in range(40):
        link_to_contact = random.choice([True, False])
        activity = Activity(
            activity_type=random.choice(ACTIVITY_TYPES),
            subject=fake.sentence(nb_words=6).rstrip("."),
            description=fake.sentence(nb_words=15),
            activity_date=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
            contact_id=random.choice(contacts).id if link_to_contact and contacts else None,
            lead_id=random.choice(leads).id if not link_to_contact and leads else None,
            owner_id=random.choice(reps).id,
        )
        db.session.add(activity)
        activities.append(activity)

    db.session.commit()
    print(f"Created {len(activities)} activities.")
    print("Seeding complete.")


if __name__ == "__main__":
    with app.app_context():
        seed()