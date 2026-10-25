from app import create_app, db
from app.models import Contact

app = create_app()
with app.app_context():
    seen, dupes = {}, []
    for c in Contact.query.order_by(Contact.id).all():
        if not c.email:
            continue
        key = c.email.lower()
        if key in seen:
            dupes.append(c)
        else:
            seen[key] = c.id
    print(f"Found {len(dupes)} duplicate contact(s)")
    if input("Delete them? (yes/no): ").strip().lower() == "yes":
        for c in dupes:
            db.session.delete(c)
        db.session.commit()
        print("Deleted.")