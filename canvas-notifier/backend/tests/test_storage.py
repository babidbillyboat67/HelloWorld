import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import storage


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(storage, "DB_PATH", path)
    storage.init_db()
    yield
    os.remove(path)


def test_create_and_get_user():
    user_id = storage.create_user("Ada", "https://canvas.example.edu/", "tok123")
    user = storage.get_user(user_id)
    assert user["name"] == "Ada"
    assert user["canvas_url"] == "https://canvas.example.edu"  # trailing slash stripped
    assert user["canvas_token"] == "tok123"


def test_get_user_missing_returns_none():
    assert storage.get_user(999) is None


def test_push_subscription_upsert_by_endpoint():
    user_id = storage.create_user("Ada", "https://canvas.example.edu", "tok")
    storage.add_push_subscription(user_id, "https://push/ep1", "p256dh-a", "auth-a")
    storage.add_push_subscription(user_id, "https://push/ep1", "p256dh-b", "auth-b")

    subs = storage.get_subscriptions(user_id)
    assert len(subs) == 1
    assert subs[0]["p256dh"] == "p256dh-b"


def test_remove_subscription():
    user_id = storage.create_user("Ada", "https://canvas.example.edu", "tok")
    storage.add_push_subscription(user_id, "https://push/ep1", "p", "a")
    storage.remove_subscription("https://push/ep1")
    assert storage.get_subscriptions(user_id) == []


def test_notification_dedupe():
    user_id = storage.create_user("Ada", "https://canvas.example.edu", "tok")
    assert not storage.has_been_notified(user_id, "assignment-1", "24h")
    storage.mark_notified(user_id, "assignment-1", "24h")
    assert storage.has_been_notified(user_id, "assignment-1", "24h")
    assert not storage.has_been_notified(user_id, "assignment-1", "1h")
