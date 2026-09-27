from app import create_app, db

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # creates tables from models.py if they don't exist yet
    app.run(debug=True)
