from datetime import datetime

import google.generativeai as genai
from flask import current_app

STAGE_POINTS = {"New": 10, "Contacted": 25, "Qualified": 40, "Proposal Sent": 55}
SOURCE_POINTS = {"Referral": 10, "Walk-in": 10, "Website": 6, "Social Media": 3, "Other": 0}


def score_lead(lead, last_activity=None):
    """Rule-based score. Returns None for closed leads (Won / Lost)."""
    if lead.stage in ("Won", "Lost"):
        return None

    points = STAGE_POINTS.get(lead.stage, 0)

    value = float(lead.estimated_value or 0)
    if value >= 2000:
        points += 20
    elif value >= 1000:
        points += 12
    elif value >= 500:
        points += 6

    points += SOURCE_POINTS.get(lead.source, 0)

    if last_activity:
        days = (datetime.utcnow() - last_activity).days
        if days <= 7:
            points += 15
        elif days <= 30:
            points += 8

    label = "Hot" if points >= 65 else "Warm" if points >= 35 else "Cold"
    return {"label": label, "points": points}


FALLBACK_ACTIONS = {
    "New": "Make first contact today: call or email to introduce yourself and learn what they need.",
    "Contacted": "Follow up with product details and offer a store visit or demo.",
    "Qualified": "Prepare a tailored quote and schedule a call to walk through it.",
    "Proposal Sent": "Check in on the proposal and ask if they have questions or need a small incentive to decide.",
    "Won": "Send a thank-you note and ask for a referral.",
    "Lost": "Log the reason it was lost and add a reminder to re-contact in a few months.",
}


def fallback_next_action(lead):
    return FALLBACK_ACTIONS.get(lead.stage, "Follow up with the lead and log the conversation.")


def suggest_next_action(lead, last_activity=None, activity_count=0):
    """Ask Gemini for one next step. Raises on any API error."""
    genai.configure(api_key=current_app.config.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-flash-latest")

    if last_activity:
        days = (datetime.utcnow() - last_activity).days
        recency = f"{days} day(s) since the last logged activity"
    else:
        recency = "no activity logged yet"

    prompt = f"""You are a sales coach for an electronics retail CRM.
Suggest ONE specific next action for the sales rep. Reply with a single sentence, at most 25 words, and nothing else.

Lead: {lead.first_name} {lead.last_name}
Stage: {lead.stage}
Source: {lead.source or 'unknown'}
Product interest: {lead.product_interest or 'unknown'}
Estimated value: {lead.estimated_value or 'unknown'}
Activities logged: {activity_count} ({recency})
Notes: {(lead.notes or 'none')[:300]}
"""
    response = model.generate_content(prompt)
    return response.text.strip()