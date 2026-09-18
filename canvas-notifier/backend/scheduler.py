"""Background job: periodically re-syncs every registered student's Canvas
courses and pushes a phone notification when an assignment or test crosses
one of the reminder windows below.
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

import canvas_client
import storage
from notifications import PushError, send_push

logger = logging.getLogger("canvas_notifier.scheduler")

# (stage name, how close to the due date this reminder fires)
REMINDER_STAGES = [
    ("24h", timedelta(hours=24)),
    ("1h", timedelta(hours=1)),
]


def _parse_due(due_at):
    return datetime.fromisoformat(due_at.replace("Z", "+00:00"))


def check_and_notify_user(user):
    user_id = user["id"]
    subscriptions = storage.get_subscriptions(user_id)
    if not subscriptions:
        return

    try:
        items = canvas_client.get_upcoming_items(user["canvas_url"], user["canvas_token"])
    except canvas_client.CanvasError as exc:
        logger.warning("Canvas sync failed for user %s: %s", user_id, exc)
        return

    now = datetime.now(timezone.utc)
    for item in items:
        try:
            due = _parse_due(item["due_at"])
        except ValueError:
            continue

        time_left = due - now
        if time_left.total_seconds() < 0:
            continue

        for stage, window in REMINDER_STAGES:
            if time_left > window or storage.has_been_notified(user_id, item["id"], stage):
                continue

            kind = "Test" if item["type"] == "test" else "Assignment"
            title = f"{kind} due soon: {item['name']}"
            body = f"{item['course']} — due {due.strftime('%a %b %d, %I:%M %p UTC')}"

            for sub in subscriptions:
                try:
                    send_push(sub, title, body, url=item.get("html_url"))
                except PushError as exc:
                    logger.warning("Push failed for user %s: %s", user_id, exc)
                    if "410" in str(exc) or "404" in str(exc):
                        storage.remove_subscription(sub["endpoint"])

            storage.mark_notified(user_id, item["id"], stage)


def run_sync_cycle():
    for user in storage.list_users():
        check_and_notify_user(user)


def start_scheduler(interval_minutes=15):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_sync_cycle,
        "interval",
        minutes=interval_minutes,
        next_run_time=datetime.now(),
    )
    scheduler.start()
    return scheduler
