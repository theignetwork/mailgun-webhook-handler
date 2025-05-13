from flask import Flask, request, jsonify
import os
import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

app = Flask(__name__)

@app.route("/webhook/mailgun", methods=["POST"])
def mailgun_webhook():
    data = request.form.to_dict()
    event_type = data.get("event")
    recipient_email = data.get("recipient")

    if not event_type or not recipient_email:
        return jsonify({"error": "Missing event or recipient"}), 400

    now = datetime.datetime.utcnow().isoformat()

    suppression_reason = {
        "bounced": "hard_bounce",
        "complained": "complaint",
        "unsubscribed": "unsubscribe_link",
    }.get(event_type)

    if suppression_reason:
        # 1. Add to suppression_list
        supabase.table("suppression_list").upsert({
            "email": recipient_email.lower(),
            "reason_code": suppression_reason,
            "timestamp": now,
        }, on_conflict=["email"]).execute()

        # 2. Set send_allowed = FALSE
        supabase.table("edu_contacts").update({
            "send_allowed": False
        }).eq("email", recipient_email.lower()).execute()

        # 3. Log to edu_outreach_events
        supabase.table("edu_outreach_events").insert({
            "event_type": f"p8_email_{event_type}",
            "payload": {"email": recipient_email},
        }).execute()

        return jsonify({"status": "suppressed"}), 200

    return jsonify({"ignored": True}), 200

if __name__ == "__main__":
    app.run(debug=True)
