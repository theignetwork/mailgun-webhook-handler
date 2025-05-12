
from fastapi import FastAPI, Request
import logging
import os

app = FastAPI()

# Basic logging
logging.basicConfig(level=logging.INFO)

@app.post("/webhook")
async def handle_mailgun_event(request: Request):
    payload = await request.json()
    logging.info("Received webhook event: %s", payload)
    return {"status": "ok"}
