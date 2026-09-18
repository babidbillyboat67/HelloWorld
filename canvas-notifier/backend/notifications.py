"""Sends a single Web Push notification using VAPID auth."""

import json
import os

from pywebpush import WebPushException, webpush


class PushError(Exception):
    pass


def send_push(subscription, title, body, url=None):
    private_key = os.environ.get("VAPID_PRIVATE_KEY")
    if not private_key:
        raise PushError("VAPID_PRIVATE_KEY is not configured on the server")
    claims_email = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:admin@example.com")

    payload = json.dumps({"title": title, "body": body, "url": url or "/"})
    subscription_info = {
        "endpoint": subscription["endpoint"],
        "keys": {
            "p256dh": subscription["p256dh"],
            "auth": subscription["auth"],
        },
    }
    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims={"sub": claims_email},
        )
    except WebPushException as exc:
        raise PushError(str(exc)) from exc
