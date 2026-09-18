"""FastAPI backend for Canvas Notifier.

Students register their Canvas URL + API token once, subscribe their phone
to Web Push, and a background job (see scheduler.py) polls Canvas and pushes
a notification when an assignment or test is coming due.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import canvas_client
import storage
from scheduler import start_scheduler

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Canvas Notifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

storage.init_db()
_scheduler = None


@app.on_event("startup")
def _on_startup():
    global _scheduler
    interval = int(os.environ.get("SYNC_INTERVAL_MINUTES", "15"))
    _scheduler = start_scheduler(interval)


@app.on_event("shutdown")
def _on_shutdown():
    if _scheduler:
        _scheduler.shutdown(wait=False)


class RegisterRequest(BaseModel):
    name: str
    canvas_url: str
    canvas_token: str


class SubscribeRequest(BaseModel):
    user_id: int
    endpoint: str
    p256dh: str
    auth: str


@app.post("/api/register")
def register(req: RegisterRequest):
    try:
        canvas_client.get_active_courses(req.canvas_url, req.canvas_token)
    except canvas_client.CanvasError as exc:
        raise HTTPException(
            status_code=400, detail=f"Could not verify Canvas credentials: {exc}"
        )
    user_id = storage.create_user(req.name, req.canvas_url, req.canvas_token)
    return {"user_id": user_id}


@app.get("/api/vapid-public-key")
def vapid_public_key():
    key = os.environ.get("VAPID_PUBLIC_KEY")
    if not key:
        raise HTTPException(
            status_code=500, detail="VAPID_PUBLIC_KEY is not configured on the server"
        )
    return {"key": key}


@app.post("/api/push/subscribe")
def subscribe(req: SubscribeRequest):
    if not storage.get_user(req.user_id):
        raise HTTPException(status_code=404, detail="Unknown user_id")
    storage.add_push_subscription(req.user_id, req.endpoint, req.p256dh, req.auth)
    return {"status": "subscribed"}


@app.get("/api/assignments/{user_id}")
def assignments(user_id: int):
    user = storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Unknown user_id")
    try:
        items = canvas_client.get_upcoming_items(user["canvas_url"], user["canvas_token"])
    except canvas_client.CanvasError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"items": items}


# Serve the PWA itself from this same service, so a deployment only needs one
# URL and never has to deal with cross-origin push subscriptions. Mounted
# last so it never shadows the /api/* routes above.
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
