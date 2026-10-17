# AarogyaSaathi

A voice-first, privacy-respecting care companion for elders and their families.
The elder decides what is shared. Nothing leaves without an active consent record.

Live demo : https://srilaasya487.github.io/SaarthiX-DocBuddy/

## The problem
India has 150M+ people aged 60+. Many live apart from their children, struggle with small text and English apps, miss medicines, and are targets of phone scams. Family worries; seniors feel watched.

## Our answer
- Voice in, voice out, 8 Indian languages, large buttons, "hear again" and "slow down".
- Consent first:the senior chooses who sees what, for how long, and can revoke by voice. A spoken audit log answers "who saw my information?".
- Safety: SOS, fall detection with a 60-second "Are you okay?", scam checker, emergency card.
- Medicines: reminders, low-stock alerts, prescription scan, pillbox photo check.
- Family portal shows only what the senior allowed, plus a care-team task board.
- ASHA / partner portal for community health workers, with anonymous area statistics.
- Works on slow phones and offline (queued actions sync later).

## Try it in 2 minutes (demo script)
1. Open the link, tap **Try the demo as Sarala**. Point out the large buttons and spoken greeting.
2. **My medicines** → tap *I took it*. The badge clears.
3. **Daily check-in** → answer "Not well" → the app *asks Sarala* before telling family.
4. **Who can see what** → show current sharing, tap *Stop*, then *Who saw my information?*
5. Home → **Please check** → approve Rohan's request to see her mood.
6. Tap **⚠ Simulate fall** → "Are you okay?" → no answer escalates to contacts (real backend).
7. **Staying safe → Is this a scam?** → paste "Your KYC is blocked, share OTP".
8. Sign out → **Try the demo as Rohan** → show the family view with only the shared items.

## Honest status
The live site runs on built-in sample data so anyone can click through it. The real FastAPI backend, consent engine, audit log and 43 tests are in `backend/`. See `docs/IMPLEMENTATION.md` for what is and is not proven. SMS, WhatsApp and IVR channels are stubs.

## Run the full stack locally
    cd backend && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --reload
    cd frontend && cp .env.example .env && npm install && npm run dev
Set `VITE_API_URL` to use a real backend instead of demo mode.
