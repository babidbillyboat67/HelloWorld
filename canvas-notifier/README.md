# Canvas Notifier

A small app that syncs to Canvas LMS and sends real push notifications to a
student's phone before their assignments and tests are due.

It's two pieces:

- **`backend/`** — a FastAPI service that logs into Canvas on the student's
  behalf, polls for upcoming assignments/tests, and sends
  [Web Push](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)
  notifications on a schedule.
- **`frontend/`** — a installable PWA (Progressive Web App). A student opens
  it once, adds it to their phone's home screen, and taps "enable
  notifications" — no app store needed, and it works on both Android and iOS
  16.4+.

## How the reminders work

Every `SYNC_INTERVAL_MINUTES` (default 15), the backend re-fetches each
registered student's active courses and assignments from Canvas, and pushes
a notification the first time an item crosses:

- **24 hours** before it's due
- **1 hour** before it's due

Each (student, item, stage) reminder is only ever sent once, so a sync
running every 15 minutes won't spam the same reminder repeatedly.

Quizzes/exams that are graded through Canvas show up via the same
assignments endpoint Canvas uses, so they're included automatically and
labeled "Test" instead of "Assignment" (based on submission type / keywords
in the title — see `classify_assignment` in `backend/canvas_client.py`).

## 1. Set up the backend

```bash
cd canvas-notifier/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Generate a VAPID key pair (this is what lets the backend push notifications
without a third-party service like Firebase):

```bash
python generate_vapid_keys.py
```

Copy `.env.example` to `.env` and paste in the printed keys:

```bash
cp .env.example .env
# then edit .env and fill in VAPID_PRIVATE_KEY / VAPID_PUBLIC_KEY
```

Run it:

```bash
uvicorn app:app --reload --port 8000
```

Run the test suite:

```bash
pytest
```

## 2. Set up the frontend

The frontend is static files, but service workers (needed for push) require
being served over HTTP(S), not opened as a `file://` page.

```bash
cd canvas-notifier/frontend
python3 -m http.server 8090
```

If your backend isn't at the default `http://127.0.0.1:8000`, edit
`frontend/config.js` and change `CANVAS_NOTIFIER_BACKEND_URL`.

Open `http://127.0.0.1:8090` in a browser to try it locally.

### Putting it on an actual phone

Browsers only allow push notifications over HTTPS (localhost is exempted,
a phone on your Wi-Fi is not). To try this on a real phone:

1. Deploy `backend/` somewhere reachable over HTTPS (Render, Fly.io, a VPS
   behind a reverse proxy, etc.) and point `frontend/config.js` at that URL.
2. Deploy `frontend/` as static files behind HTTPS too (Netlify, Vercel,
   GitHub Pages, or served by the same host as the backend).
3. On the phone, open the frontend URL in the browser, then use the
   browser's "Add to Home Screen" / "Install app" option.
4. Open the installed app, connect your Canvas account, and tap "Enable
   notifications on this phone".

## 3. Getting a Canvas access token

In Canvas: **Account → Settings → scroll to "Approved Integrations" →
"+ New Access Token"**. Give it any purpose name and generate it. Paste that
token (and your Canvas URL, e.g. `https://yourschool.instructure.com`) into
the app's setup form — it's stored only in the backend's local SQLite
database (`backend/canvas_notifier.db`, gitignored) and used solely to read
your own assignments.

## Known limitations

- Only graded quizzes/exams are picked up (they appear through the same
  Canvas "assignments" endpoint). Ungraded practice quizzes and
  calendar-only events aren't currently synced.
- Notifications require the backend process to keep running (it's the
  thing polling Canvas and calling the push service) — this is meant to run
  on a small always-on server, not a laptop that sleeps.
- Canvas API tokens are stored in plaintext in the local SQLite database.
  Fine for personal/self-hosted use; encrypt at rest before sharing this
  with anyone else.
