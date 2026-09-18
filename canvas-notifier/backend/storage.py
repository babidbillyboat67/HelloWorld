"""SQLite-backed storage for registered students, their push subscriptions,
and which due-date reminders have already been sent (so we don't repeat them).
"""

import os
import sqlite3
import threading

DB_PATH = os.environ.get(
    "CANVAS_NOTIFIER_DB",
    os.path.join(os.path.dirname(__file__), "canvas_notifier.db"),
)

_lock = threading.Lock()


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                canvas_url TEXT NOT NULL,
                canvas_token TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                endpoint TEXT NOT NULL UNIQUE,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_notifications (
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, item_id, stage)
            )
            """
        )
        conn.commit()


def create_user(name, canvas_url, canvas_token):
    with _lock, get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, canvas_url, canvas_token) VALUES (?, ?, ?)",
            (name, canvas_url.rstrip("/"), canvas_token),
        )
        conn.commit()
        return cur.lastrowid


def get_user(user_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def list_users():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
        return [dict(r) for r in rows]


def add_push_subscription(user_id, endpoint, p256dh, auth):
    with _lock, get_connection() as conn:
        conn.execute(
            """
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(endpoint) DO UPDATE SET
                user_id = excluded.user_id,
                p256dh = excluded.p256dh,
                auth = excluded.auth
            """,
            (user_id, endpoint, p256dh, auth),
        )
        conn.commit()


def get_subscriptions(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM push_subscriptions WHERE user_id = ?", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def remove_subscription(endpoint):
    with _lock, get_connection() as conn:
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
        conn.commit()


def has_been_notified(user_id, item_id, stage):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM sent_notifications WHERE user_id = ? AND item_id = ? AND stage = ?",
            (user_id, item_id, stage),
        ).fetchone()
        return row is not None


def mark_notified(user_id, item_id, stage):
    with _lock, get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sent_notifications (user_id, item_id, stage) VALUES (?, ?, ?)",
            (user_id, item_id, stage),
        )
        conn.commit()
