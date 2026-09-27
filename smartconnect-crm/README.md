# SmartConnect CRM

## Setup

1. Create a virtual environment:
   python -m venv venv
   venv\Scripts\activate      (Windows)
   source venv/bin/activate   (Mac/Linux)

2. Install dependencies:
   pip install -r requirements.txt

3. Create a MySQL database:
   CREATE DATABASE smartconnect_crm;

4. Copy .env.example to .env and fill in your real SECRET_KEY and DATABASE_URL.

5. Run the app:
   python run.py

6. Open http://127.0.0.1:5000/register in your browser, create an account, then log in.

## What's included so far
- User model (Users table)
- Register / Login / Logout (Flask-Login + bcrypt password hashing)
- Role field (admin / sales_rep) with a role_required decorator ready for admin-only routes
- A protected dashboard page to confirm login works

## Next to build
- Contacts and Leads models + CRUD routes
- Activity tracking
- Email templates + campaigns
- AI features (email generator, lead summary, recommendations)
- Analytics dashboard
- Data import/export
