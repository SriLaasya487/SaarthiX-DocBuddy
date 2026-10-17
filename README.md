# DocBuddy

A voice-first, privacy-respecting care companion for elders and their families.
The elder decides what is shared; nothing leaves without an active consent record.

## Structure
- `backend/`  FastAPI + SQLAlchemy (SQLite for dev, PostgreSQL via docker-compose). OTP login, consent engine, audit log, medicines, check-in, vitals, doctor-type suggestion, SOS, fall countdown, family summary.
- `frontend/` React + Vite. Elder app (large buttons, voice in/out, Hear again / Slow down, SOS, fall prompt) and Family portal.
- `docs/`     Feature catalog (90 features), roadmap, principles, architecture.
- `data/`     Catalog as CSV/JSON.

## Run locally
```bash
# backend
cd backend && pip install -r requirements.txt && cp .env.example .env
uvicorn app.main:app --reload            # http://localhost:8000/docs
pytest                                    # 6 tests: consent gate, audit, SOS, fall, vitals...

# frontend
cd frontend && cp .env.example .env && npm install && npm run dev   # http://localhost:5173
```
Or everything at once: `docker compose up --build`.

Dev mode (`DEBUG=true`) returns the OTP in the API response so you can sign in without an SMS gateway.
Create an elder and a family user (two browser profiles), then as the elder open **Who can see what**.

## What is implemented vs. planned
Implemented: voice sign-up/language, OTP login, consent (per data type, temporary, revoke, spoken audit log),
daily 5-question check-in, medicine reminders + stock alert + missed-dose note, doctor-type suggestion (never diagnoses),
voice vitals logging with flags, appointments, emergency card, SOS, fall detection + 60s escalation,
ask-elder-first help alerts, mood-pattern note, weekly report with good-news, family portal (consented sections only).

Stubs / next: `services/notify.py` (WhatsApp/SMS/FCM), IVR check-in, Bhashini/AI4Bharat speech
(swap `frontend/src/voice.js`), OCR prescription scan, offline mode, multi-caregiver roles, and the rest of `docs/ROADMAP.md`.


## v2: all 90 catalogue features are in the code

See `docs/IMPLEMENTATION.md` for the feature-by-feature map (verified by a test) and, importantly, the list of what is **not** proven.

```bash
cd backend && pip install -r requirements.txt && python -m pytest      # 43 tests, incl. the 90-feature registry check
uvicorn app.main:app --reload                                         # http://localhost:8000/docs , /features
cd ../frontend && npm install && npm run dev
```
Delete `backend/docbuddy.db` once after upgrading (new tables/columns; migrations are not included yet).
New optional settings are in `backend/.env.example` (channels, AI companion, pricing).
