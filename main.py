import os
import logging
from fastapi import FastAPI, Request
from supabase import create_client, Client
from dotenv import load_dotenv

# ── Load .env if you run locally ────────────────────────────────────────────────
load_dotenv()

# ── Supabase credentials (must be set as env vars in Render) ───────────────────
SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SB_URL or not SB_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing")

sb: Client = create_client(SB_URL, SB_KEY)

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI()
logging.basicConfig(level=logging.INFO)


# helper: flip send_allowed = FALSE on bounce / spam / unsub
def suppress_if_needed(recipient_email: str, event: str) -> None:
    if event in ("permanent_failure", "complained", "unsubscribed"):
        sb.table("edu_contacts") \
          .update({"send_allowed": False}) \
          .eq("email", recipient_email).execute()


# ── Mailgun webhook endpoint ───────────────────────────────────────────────────
@app.post("/webhook")
async def mailgun_webhook(request: Request):
    print("DEBUG: entered webhook")

    payload = await request.json()

    # pull event & recipient from top level OR from the "event-data" wrapper
    event = (
        payload.get("event")
        or payload.get("event-data", {}).get("event")
    )
    recipient = (
        payload.get("recipient")
        or payload.get("event-data", {}).get("recipient")
    )

    try:
        # 1) store raw event
        sb.table("mailgun_events").insert({
            "event_type": f"p8_{event}",
            "payload": payload
        }).execute()

        # 2) auto-suppress bad addresses
        suppress_if_needed(recipient, event)

        logging.info("Stored %s → %s", event, recipient)
    except Exception as e:
        logging.error("Supabase insert failed: %s", e)

    print("DEBUG: leaving webhook")
    return {"status": "ok"}
