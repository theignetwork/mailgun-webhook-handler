import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from supabase import create_client, Client

# Load env vars
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY.")

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()
logging.basicConfig(level=logging.INFO)


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/webhook")
async def mailgun_webhook(request: Request):
    logging.debug("entered webhook")
    payload = await request.json()

    event = (
        payload.get("event") or
        payload.get("event-data", {}).get("event")
    )
    recipient_email = (
        payload.get("recipient") or
        payload.get("event-data", {}).get("recipient")
    )

    contact_id = None
    if recipient_email:
        try:
            lookup = sb.table("edu_contacts")\
                .select("id")\
                .eq("email", recipient_email)\
                .limit(1).execute()
            if lookup.data:
                contact_id = lookup.data[0]["id"]
        except Exception as e:
            logging.warning(f"Contact lookup failed for {recipient_email}: {e}")

    # 1) Store the raw event
    try:
        sb.table("mailgun_events").insert({
            "event_type": f"p8_{event}",
            "contact_id": contact_id,
            "payload": payload
        }).execute()
    except Exception as e:
        logging.error(f"Failed to insert mailgun_event: {e}")

    # 2) Auto-suppress if bounce, complaint, or unsubscribe
    if event in ["failed", "complained", "unsubscribed"] and contact_id:
        try:
            sb.table("edu_contacts")\
                .update({"send_allowed": False})\
                .eq("id", contact_id).execute()
            logging.info(f"Suppressed contact {contact_id} ({recipient_email}) due to {event}.")
        except Exception as e:
            logging.error(f"Failed to suppress {recipient_email}: {e}")

    logging.debug("leaving webhook")
    return JSONResponse(content={"status": "ok"})
