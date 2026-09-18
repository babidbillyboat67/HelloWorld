# Canvas Notifier

A small app that syncs to Canvas LMS and sends real push notifications to a
student's phone before their assignments and tests are due.

It's one FastAPI service (`backend/`) that both talks to Canvas and serves
the installable PWA (`frontend/`) — so there's a single process and a single
URL to deploy. A student opens that URL once, adds it to their phone's home
screen, and taps "enable notifications" — no app store needed, and it works
on both Android and iOS 16.4+.

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

## 1. Get a Canvas access token

In Canvas: **Account → Settings → scroll to "Approved Integrations" →
"+ New Access Token"**. Give it any purpose name and generate it — you'll
paste this into the app's setup form later. It's stored only in the
backend's local SQLite database (`backend/canvas_notifier.db`, gitignored)
and used solely to read your own assignments.

## 2. Run it locally (to try it out)

```bash
cd canvas-notifier/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python generate_vapid_keys.py        # prints a VAPID key pair
cp .env.example .env                 # then paste those keys into .env
uvicorn app:app --reload --port 8000
pytest                               # optional: run the test suite
```

Open `http://127.0.0.1:8000` in a browser — the same service now serves
both the API and the app itself, so there's nothing else to run.

## 3. Put it on an actual phone

Browsers only allow push notifications over HTTPS (`localhost` is
exempted, but a phone on your Wi-Fi hitting your laptop's IP is not), so you
need to deploy `backend/` somewhere with a real HTTPS URL. **Render's free
tier** is the least fussy way to do this — no server to maintain, and it
gives you HTTPS automatically:

1. Push this repo to GitHub (already done if you're reading this from the
   repo).
2. At [render.com](https://render.com), **New +** → **Web Service** → connect
   this repo.
3. Set:
   - **Root Directory**: `canvas-notifier/backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Under **Environment**, add the variables from `generate_vapid_keys.py`'s
   output: `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL`
   (don't commit these — set them in Render's dashboard, not in `.env`).
5. Deploy. Render gives you a URL like `https://your-app.onrender.com`.
6. On your phone, open that URL, then use the browser's **"Add to Home
   Screen"** (Safari, iOS 16.4+) or **"Install app"** (Chrome, Android)
   option.
7. Open the installed app, connect your Canvas account, and tap **"Enable
   notifications on this phone"**.

Any other host that runs a Python web service behind HTTPS (Fly.io, a VPS
with a reverse proxy, etc.) works the same way — the important parts are
the env vars and serving over HTTPS.

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
