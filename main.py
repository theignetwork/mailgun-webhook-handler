# main.py  — updated webhook that writes events to Supabase
import os, logging
from fastapi import FastAPI, Request
from supabase import create_client

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# ----- Supabase connection -----
SB_URL  = os.getenv("SUPABASE_URL")
SB_KEY  = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
print("DEBUG SB_URL = ", repr(SB_URL)[:120])
sb = create_client(SB_URL, SB_KEY)

# ---------- helpers ----------
def suppress_if_needed(recipient_email: str, event: str):
    """
    Turn off future outreach if the event is a hard bounce,
    spam complaint, or unsubscribe.
    """
    if event in ("permanent_failure", "complained", "unsubscribed"):
        sb.table("edu_contacts")\
          .update({"send_allowed": False})\
          .eq("email", recipient_email).execute()

# ---------- webhook ----------
@app.post("/webhook")
async def mailgun_webhook(request: Request):
    print("DEBUG: entered webhook")          # <-- add

    payload = await request.json()

    # pull event & recipient from top-level or "event-data"
    event = (
        payload.get("event") or
        payload.get("event-data", {}).get("event")
    )
    recipient = (
        payload.get("recipient") or
        payload.get("event-data", {}).get("recipient")
    )

    # (temporarily comment out Supabase work)
    # sb.table("mailgun_events").insert({
    #     "event_type": f"p8_{event}",
    #     "payload": payload
    # }).execute()
    #
    # suppress_if_needed(recipient, event)

    print("DEBUG: leaving webhook")          # <-- add
    return {"status": "ok"}
