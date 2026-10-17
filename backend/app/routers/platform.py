"""Platform: settings & accessibility, dialects, low-end/offline, channels (IVR, speaker, wearables, BLE), privacy (export/delete),
business (pricing, partners, CHW, aggregate)."""
import hashlib
import hmac
import json
import re
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import Base, get_db
from ..models import (ActivityLog, Alert, CheckIn, Consent, Device, DialectFeedback, IvrSession, Medicine, Message, NomineeEvent,
                      NomineeRequest, Org, PendingItem, Reminder, Subscription, SymptomNote, User, Vital, ChwVisit, DoseLog, now)
from ..security import current_user, device_elder, require_elder, require_role
from ..services import alerts as A
from ..services import assistant, insights, kv
from ..services import consent as C
from ..services import pricing as P
from ..services import rules
from ..services.notify import notify_user
from ..services.vitals import is_flagged
from .health import appts_due, card_dict, due as meds_due

router = APIRouter(tags=["platform"])
DATA = Path(__file__).resolve().parent.parent / "data"


# ---------- settings + accessibility (DB-077) + low-end (DB-076) ----------
@router.get("/settings")
def get_settings(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return kv.settings_of(db, user.id)


@router.put("/settings")
def put_settings(body: dict, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    unknown = [k for k in body if k not in kv.DEFAULT_SETTINGS]
    if unknown:
        raise HTTPException(400, f"Unknown settings: {unknown}")
    if "font_scale" in body:
        body["font_scale"] = max(1.0, min(2.0, float(body["font_scale"])))
    if "speech_rate" in body:
        body["speech_rate"] = max(0.5, min(1.5, float(body["speech_rate"])))
    cur = kv.get(db, user.id, "settings", {}) or {}
    kv.put(db, user.id, "settings", {**cur, **body})
    return kv.settings_of(db, user.id)


@router.get("/lite/home")
def lite_home(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """One small response with everything the home screen needs: fewer requests and bytes for low-end phones and weak networks.
    The app caches this for offline use."""
    from .life import disaster_get
    from .records import reminders_today
    unread = db.scalars(select(Message).where(Message.elder_id == user.id, Message.played.is_(False), Message.kind != "imfine")).all()
    return {"name": user.name, "language": user.language, "due": meds_due(user, db), "appointments": appts_due(user, db),
            "reminders": reminders_today(user, db), "pending": len(db.scalars(select(PendingItem).where(PendingItem.elder_id == user.id, PendingItem.status == "pending")).all()),
            "unread_messages": len(unread), "nudges": insights.nudges_due(db, user.id, datetime.now().hour), "disaster": disaster_get(user, db)["on"],
            "medicines": [{"name": m.name, "times": m.times, "tablets": m.tablets} for m in db.scalars(select(Medicine).where(Medicine.elder_id == user.id, Medicine.active)).all()],
            "server_time": now().isoformat()}


class SyncOp(BaseModel):
    client_id: str
    op: str  # dose_taken | checkin | vital | symptom | activity
    data: dict
    at: datetime | None = None


class SyncReq(BaseModel):
    ops: list[SyncOp]


@router.post("/sync/batch")
def sync(body: SyncReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Offline queue replay. Each op is applied once (client_id) and keeps its ORIGINAL timestamp."""
    seen = set(kv.get(db, user.id, "synced", []) or [])
    results = []
    for o in body.ops:
        if o.client_id in seen:
            results.append({"client_id": o.client_id, "status": "duplicate"}); continue
        at = o.at.replace(tzinfo=None) if o.at else now()
        d = o.data
        try:
            if o.op == "dose_taken":
                m = db.get(Medicine, int(d["medicine_id"]))
                if not m or m.elder_id != user.id: raise ValueError("medicine")
                db.add(DoseLog(medicine_id=m.id, elder_id=user.id, slot=d["slot"], taken_at=at)); m.stock = max(0, m.stock - m.tablets)
            elif o.op == "checkin":
                db.add(CheckIn(elder_id=user.id, at=at, mood=d.get("mood", "okay"), pain=d.get("pain", "none"), took_medicines=bool(d.get("took_medicines", True)),
                               needs_help=bool(d.get("needs_help", False)), doctor_visit_soon=bool(d.get("doctor_visit_soon", False)), note=d.get("note", "")))
                if d.get("needs_help") or d.get("pain") == "strong":
                    A.ask_elder(db, user.id, "help", "Needs help.")  # still waits for the elder's yes
            elif o.op == "vital":
                db.add(Vital(elder_id=user.id, kind=d["kind"], value1=float(d["value1"]), value2=d.get("value2"), flagged=is_flagged(d["kind"], float(d["value1"]), d.get("value2")),
                             source="offline", at=at))
            elif o.op == "symptom":
                db.add(SymptomNote(elder_id=user.id, text=d["text"], at=at))
            elif o.op == "activity":
                db.add(ActivityLog(elder_id=user.id, kind=d["kind"], value=float(d.get("value", 1)), at=at))
            else:
                raise ValueError("op")
            db.commit(); seen.add(o.client_id); results.append({"client_id": o.client_id, "status": "ok"})
        except (KeyError, ValueError, TypeError):
            db.rollback(); results.append({"client_id": o.client_id, "status": "rejected"})
    kv.put(db, user.id, "synced", list(seen)[-500:])
    return {"results": results}


# ---------- dialects (DB-075) ----------
@router.get("/dialect/lexicon")
def lexicon():
    return json.loads((DATA / "dialects.json").read_text(encoding="utf-8"))


class NormReq(BaseModel):
    text: str
    dialect: str = ""


@router.post("/dialect/normalize")
def normalize(body: NormReq):
    lex, t = lexicon(), body.text.lower()
    hits: list[tuple[int, str]] = []
    phrases = list(lex["dialects"].get(body.dialect, {}).items()) + [(w, i) for i, ws in lex["intents"].items() for w in ws]
    for phrase, intent in phrases:
        for m in re.finditer(rf"(?<!\w){re.escape(phrase.lower())}(?!\w)", t):
            hits.append((m.start(), intent))
    hits.sort()
    order = list(dict.fromkeys(i for _, i in hits))
    if "yes" in order and "no" in order:  # 'haan nahi' - the LAST answer wins
        last = max((p, i) for p, i in hits if i in {"yes", "no"})[1]
        order = [i for i in order if i not in {"yes", "no"}] + [last]
    return {"intents": order}


class FeedbackIn(BaseModel):
    heard: str
    meant: str
    dialect: str = ""


@router.post("/dialect/feedback")
def feedback(body: FeedbackIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    db.add(DialectFeedback(elder_id=user.id, **body.model_dump())); db.commit()
    return {"ok": True, "note": "Thank you - this helps DocBuddy understand your way of speaking."}


# ---------- devices (DB-029), wearables / smart speakers (DB-078) ----------
class DeviceIn(BaseModel):
    kind: str  # bp | glucometer | oximeter | watch | speaker
    ident: str = ""


@router.post("/devices")
def device_add(body: DeviceIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    P.gate(db, user.id, "devices")
    d = Device(elder_id=user.id, kind=body.kind, ident=body.ident, token=secrets.token_urlsafe(24)); db.add(d); db.commit()
    return {"id": d.id, "token": d.token, "note": "Put this token in the speaker/watch app as X-Device-Token."}


@router.get("/devices")
def devices(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return [{"id": d.id, "kind": d.kind, "ident": d.ident, "last_sync": d.last_sync} for d in db.scalars(select(Device).where(Device.elder_id == user.id)).all()]


class Reading(BaseModel):
    kind: str
    value1: float
    value2: float | None = None
    at: datetime | None = None


class ReadingsIn(BaseModel):
    readings: list[Reading]


@router.post("/devices/readings")
def device_readings(body: ReadingsIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Readings pulled over Bluetooth by the phone app (BP monitor, glucometer, oximeter)."""
    n, flagged = 0, 0
    for r in body.readings:
        if r.kind not in {"bp", "sugar", "spo2", "pulse"}: continue
        f = is_flagged(r.kind, r.value1, r.value2)
        db.add(Vital(elder_id=user.id, kind=r.kind, value1=r.value1, value2=r.value2, flagged=f, source="device", at=(r.at.replace(tzinfo=None) if r.at else now())))
        n += 1; flagged += f
    for d in db.scalars(select(Device).where(Device.elder_id == user.id)).all(): d.last_sync = now()
    db.commit()
    return {"saved": n, "flagged": flagged}


class WearableIn(BaseModel):
    hr: float | None = None
    spo2: float | None = None
    steps: float | None = None
    sleep_hours: float | None = None
    fall: bool = False
    location: str = ""


@router.post("/wearables/push")
def wearable_push(body: WearableIn, dev=Depends(device_elder), db: Session = Depends(get_db)):
    eid = dev.elder_id
    dev.last_sync = now()
    if body.hr is not None:
        db.add(Vital(elder_id=eid, kind="pulse", value1=body.hr, flagged=is_flagged("pulse", body.hr, None), source="wearable"))
    if body.spo2 is not None:
        db.add(Vital(elder_id=eid, kind="spo2", value1=body.spo2, flagged=is_flagged("spo2", body.spo2, None), source="wearable"))
    if kv.settings_of(db, eid)["activity_tracking"]:  # passive data only with opt-in
        for k, v in (("steps", body.steps), ("sleep", body.sleep_hours)):
            if v is not None: db.add(ActivityLog(elder_id=eid, kind=k, value=v, source="wearable"))
    db.commit()
    out = {"ok": True}
    if body.fall:
        out["alert_id"] = A.start_fall_countdown(db, eid, body.location).id
    return out


class SpeakerIn(BaseModel):
    text: str
    confirm: bool = False


@router.post("/speaker/webhook")
def speaker(body: SpeakerIn, dev=Depends(device_elder), db: Session = Depends(get_db)):
    """Alexa / Google Nest bridge. Same assistant as the app; risky actions (SOS) need a spoken 'confirm' second call."""
    elder = db.get(User, dev.elder_id)
    r = assistant.intent(body.text)
    if r["intent"] == "medicines":
        due_ = meds_due(elder, db)
        return {"speech": " ".join(d["speak"] for d in due_) or "No medicines are due right now."}
    if r["intent"] == "sos":
        if not body.confirm:
            return {"speech": "Do you want me to send an emergency alert? Say confirm.", "needs_confirm": True}
        a = Alert(elder_id=elder.id, kind="sos", message=f"SOS via speaker. Emergency card: {card_dict(db, elder.id)}"); db.add(a); db.commit()
        return {"speech": f"I told {A.dispatch(db, a)} people. Please also call 112.", "alert_id": a.id}
    if r["intent"] == "imfine":
        from .care import imfine
        return {"speech": imfine(True, elder, db)["speak"]}
    return {"speech": r["speak"] or assistant.chat(body.text)["reply"]}


# ---------- phone-call IVR (DB-025, DB-079) ----------
IVR_Q = [("mood", "How are you feeling? Press 1 for good, 2 for okay, 3 for not well.", {"1": "good", "2": "okay", "3": "low"}),
         ("pain", "Do you have pain? Press 1 for none, 2 for a little, 3 for strong pain.", {"1": "none", "2": "mild", "3": "strong"}),
         ("meds", "Have you taken your medicines? Press 1 for yes, 2 for no.", {"1": True, "2": False}),
         ("help", "Do you need help today? Press 1 for no, 2 for yes.", {"1": False, "2": True}),
         ("visit", "Do you have a doctor visit soon? Press 1 for no, 2 for yes.", {"1": False, "2": True})]


def _twiml(say: str, gather: bool = True, lang: str = "en-IN", hangup: bool = False) -> Response:
    body = f'<Say language="{lang}">{escape(say)}</Say>'
    if gather:
        body = f'<Gather numDigits="1" timeout="8" action="/ivr/incoming" method="POST">{body}</Gather><Say language="{lang}">I did not hear you. Goodbye.</Say>'
    if hangup:
        body += "<Hangup/>"
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>', media_type="application/xml")


@router.post("/ivr/incoming")
async def ivr(request: Request, db: Session = Depends(get_db)):
    """Webhook for Twilio/Exotel-style providers (form-encoded From, Digits). Works on any feature phone. Press 9 any time = SOS, 0 = hear medicines."""
    if settings.ivr_provider_key and request.query_params.get("key") != settings.ivr_provider_key:
        raise HTTPException(403, "Bad webhook key")
    form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    phone = re.sub(r"\D", "", form.get("From", ""))[-10:]
    digit = form.get("Digits", "")
    user = next((u for u in db.scalars(select(User).where(User.role == "elder")).all() if u.phone.endswith(phone)), None) if phone else None
    if not user:
        return _twiml("Sorry, this number is not registered with DocBuddy.", False, hangup=True)
    lang = user.language or "en-IN"
    s = db.scalars(select(IvrSession).where(IvrSession.phone == phone).order_by(IvrSession.id.desc())).first()
    if not s or s.at < now() - timedelta(minutes=10) or (digit == "" and s.step > 0):
        s = IvrSession(phone=phone, elder_id=user.id, step=0, answers="{}"); db.add(s); db.commit()
        return _twiml(f"Namaste {user.name}. This is DocBuddy. " + IVR_Q[0][1], lang=lang)
    if digit == "9":
        a = Alert(elder_id=user.id, kind="sos", message=f"SOS by phone call. Emergency card: {card_dict(db, user.id)}"); db.add(a); db.commit()
        return _twiml(f"I have told {A.dispatch(db, a)} people. Please also call one one two.", False, lang, True)
    if digit == "0":
        due_ = meds_due(user, db)
        return _twiml(" ".join(d["speak"] for d in due_) or "No medicines are due right now. Goodbye.", False, lang, True)
    ans = json.loads(s.answers)
    if s.step < len(IVR_Q):
        key, _, opts = IVR_Q[s.step]
        if digit not in opts:
            return _twiml("Sorry, please press one of the numbers. " + IVR_Q[s.step][1], lang=lang)
        ans[key] = opts[digit]; s.step += 1; s.answers = json.dumps(ans); db.commit()
        if s.step < len(IVR_Q):
            return _twiml(IVR_Q[s.step][1], lang=lang)
        db.add(CheckIn(elder_id=user.id, mood=ans["mood"], pain=ans["pain"], took_medicines=ans["meds"], needs_help=ans["help"], doctor_visit_soon=ans["visit"], note="by phone call"))
        db.commit()
        if ans["help"] or ans["pain"] == "strong":
            s.step = 99; db.commit()
            return _twiml("Shall I tell your family that you need help? Press 1 for yes, 2 for no.", lang=lang)
        return _twiml("Thank you. Take care. Goodbye.", False, lang, True)
    if s.step == 99:  # elder's yes/no on informing family
        al = db.scalars(select(Alert).where(Alert.elder_id == user.id, Alert.status == "pending_elder").order_by(Alert.id.desc())).first()
        if digit == "1":
            al = al or A.ask_elder(db, user.id, "help", "Needs help (phone check-in).")
            return _twiml(f"I told {A.dispatch(db, al)} people. Take care.", False, lang, True)
        return _twiml("Okay. I will not tell anyone. Take care.", False, lang, True)
    return _twiml("Goodbye.", False, lang, True)


@router.post("/ivr/call/{elder_id}")
def ivr_call(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Ask the provider to phone the elder for the daily check-in (primary caregivers only)."""
    if C.team_role(db, elder_id, user.id) != "primary" and elder_id != user.id:
        raise HTTPException(403, "Primary caregiver only")
    P.gate(db, elder_id, "ivr")
    notify_user(db, elder_id, "DocBuddy daily check-in call. Please pick up.", elder_id, channel="ivr")
    return {"queued": True}


# ---------- privacy: export + delete (DB-085) ----------
OWNER_COLS = ("elder_id", "user_id")
ANY_USER_COLS = {"elder_id", "user_id", "grantee_id", "member_id", "proposer_id", "sender_id", "requester_id", "caller_id", "nominee_id", "actor_id",
                 "paid_by", "created_by", "set_by", "chw_id", "admin_id", "responsible_id", "payer_id"}


def _rowdict(r):
    return {c.name: (getattr(r, c.name).isoformat() if hasattr(getattr(r, c.name), "isoformat") else getattr(r, c.name)) for c in r.__table__.columns}


@router.get("/me/export")
def export(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Everything DocBuddy holds about you, including who you shared with and who accessed what (DPDP Act 2023: right to access)."""
    out = {"user": {"id": user.id, "name": user.name, "phone": user.phone, "role": user.role, "language": user.language}, "tables": {}}
    for t in Base.metadata.sorted_tables:
        cols = [c for c in t.columns if c.name in OWNER_COLS]
        if not cols or t.name in {"otp_codes", "users"}:
            continue
        rows = db.execute(select(t).where(cols[0] == user.id)).mappings().all()
        if rows:
            out["tables"][t.name] = [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(r).items()} for r in rows]
    shared = db.scalars(select(Consent).where(Consent.grantee_id == user.id)).all()
    out["shared_with_me"] = [_rowdict(c) for c in shared]
    return out


@router.delete("/me")
def delete_me(confirm: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Right to erasure. Deletes the account and every row that references it; shared media files are removed too."""
    if not confirm:
        raise HTTPException(400, "Call again with ?confirm=true. This cannot be undone.")
    uid = user.id
    mdir = Path(settings.media_dir)
    for t in ("documents", "life_stories", "messages"):
        for ref in db.execute(Base.metadata.tables[t].select().where(Base.metadata.tables[t].c.elder_id == uid)).mappings():
            if ref.get("file_ref"):
                (mdir / ref["file_ref"]).unlink(missing_ok=True)
    req_ids = [r.id for r in db.scalars(select(NomineeRequest).where((NomineeRequest.elder_id == uid) | (NomineeRequest.nominee_id == uid))).all()]
    if req_ids:
        db.execute(delete(NomineeEvent).where(NomineeEvent.request_id.in_(req_ids)))
    db.execute(delete(Base.metadata.tables["otp_codes"]).where(Base.metadata.tables["otp_codes"].c.phone == user.phone))
    for t in reversed(Base.metadata.sorted_tables):
        cols = [c for c in t.columns if c.name in ANY_USER_COLS]
        if cols and t.name != "users":
            from sqlalchemy import or_
            db.execute(delete(t).where(or_(*[c == uid for c in cols])))
    db.execute(delete(User).where(User.id == uid))
    db.commit()
    return {"deleted": True}


@router.get("/me/consent-records")
def consent_records(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(Consent).where(Consent.elder_id == user.id).order_by(Consent.id)).all()
    return [{"grantee": (db.get(User, c.grantee_id).name or db.get(User, c.grantee_id).phone), "data_type": c.data_type, "scope": c.scope, "given_at": c.created_at,
             "expires_at": c.expires_at, "revoked_at": c.revoked_at} for c in rows]


# ---------- business: pricing (DB-090), partners (DB-087), CHW (DB-088), aggregate (DB-089) ----------
@router.get("/pricing")
def pricing():
    return P.pricing()


@router.get("/billing/{elder_id}")
def billing(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not C.is_team(db, elder_id, user.id):
        raise HTTPException(403, "Not on this care team")
    return {"tier": P.tier_of(db, elder_id), "enforced": settings.enforce_tiers}


class SubIn(BaseModel):
    elder_id: int
    tier: str
    days: int = 30


@router.post("/billing/subscribe")
def subscribe(body: SubIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Dev-only shortcut. Production: the payment provider calls /billing/webhook after a successful payment."""
    if not settings.debug:
        raise HTTPException(501, "Use the payment provider flow")
    return _set_tier(db, body.elder_id, body.tier, body.days, user.id)


def _set_tier(db, elder_id, tier, days, payer):
    if tier not in P.TIERS:
        raise HTTPException(400, "Unknown tier")
    s = db.get(Subscription, elder_id) or Subscription(elder_id=elder_id)
    s.tier, s.payer_id, s.valid_until = tier, payer, now() + timedelta(days=days)
    db.add(s); db.commit()
    return {"tier": tier, "valid_until": s.valid_until}


@router.post("/billing/webhook")
async def billing_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    sig = request.headers.get("x-signature", "")
    if not hmac.compare_digest(sig, hmac.new(settings.jwt_secret.encode(), raw, hashlib.sha256).hexdigest()):
        raise HTTPException(403, "Bad signature")
    d = json.loads(raw)
    return _set_tier(db, int(d["elder_id"]), d["tier"], int(d.get("days", 30)), d.get("payer_id"))


class OrgIn(BaseModel):
    name: str
    kind: str


@router.post("/orgs")
def org_create(body: OrgIn, user: User = Depends(require_role("partner")), db: Session = Depends(get_db)):
    if body.kind not in {"hospital", "insurer", "pharmacy", "oldagehome", "corporate", "ngo", "government"}:
        raise HTTPException(400, "Unknown kind")
    o = Org(name=body.name, kind=body.kind, code=secrets.token_hex(3).upper(), admin_id=user.id); db.add(o); db.commit()
    return {"id": o.id, "code": o.code}


class JoinIn(BaseModel):
    code: str
    data_types: list[str]
    days: int | None = None


@router.post("/orgs/join")
def org_join(body: JoinIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """The elder picks EXACTLY which data types the organisation sees. Nothing is implied by joining."""
    o = db.scalars(select(Org).where(Org.code == body.code.upper())).first()
    if not o:
        raise HTTPException(404, "No organisation with that code")
    if not body.data_types:
        raise HTTPException(400, "Choose at least one thing to share")
    for t in body.data_types:
        C.grant(db, user.id, o.admin_id, t, "view", body.days)
    return {"joined": o.name, "shares": body.data_types}


@router.get("/orgs/me/elders")
def org_elders(user: User = Depends(require_role("partner", "chw")), db: Session = Depends(get_db)):
    rows = [c for c in db.scalars(select(Consent).where(Consent.grantee_id == user.id, Consent.revoked_at.is_(None))).all() if C._active(c)]
    out: dict[int, list[str]] = {}
    for c in rows:
        out.setdefault(c.elder_id, []).append(f"{c.data_type}:{c.scope}")
    return [{"id": e, "name": db.get(User, e).name, "access": a} for e, a in out.items()]


@router.get("/chw/elders")
def chw_elders(user: User = Depends(require_role("chw")), db: Session = Depends(get_db)):
    return org_elders(user, db)


class ChwVisitIn(BaseModel):
    elder_id: int
    notes: str = ""
    vitals: list[Reading] = []
    checkin: dict | None = None


@router.post("/chw/visit")
def chw_visit(body: ChwVisitIn, user: User = Depends(require_role("chw")), db: Session = Depends(get_db)):
    """Home-visit entry made ON BEHALF of the elder - allowed only with the elder's 'write' consent; everything is audit-logged and tagged source=chw."""
    saved = {"vitals": 0, "checkin": False}
    if body.vitals:
        C.require_scope(db, body.elder_id, user, "vitals", "write")
        for r in body.vitals:
            db.add(Vital(elder_id=body.elder_id, kind=r.kind, value1=r.value1, value2=r.value2, flagged=is_flagged(r.kind, r.value1, r.value2), source="chw")); saved["vitals"] += 1
    if body.checkin:
        C.require_scope(db, body.elder_id, user, "checkin", "write")
        d = body.checkin
        db.add(CheckIn(elder_id=body.elder_id, mood=d.get("mood", "okay"), pain=d.get("pain", "none"), took_medicines=bool(d.get("took_medicines", True)),
                       needs_help=bool(d.get("needs_help", False)), note=f"CHW visit {user.name}: " + d.get("note", ""))); saved["checkin"] = True
    db.add(ChwVisit(chw_id=user.id, elder_id=body.elder_id, notes=body.notes)); db.commit()
    return saved


@router.get("/insights/aggregate")
def aggregate(user: User = Depends(require_role("partner")), db: Session = Depends(get_db)):
    org = db.scalars(select(Org).where(Org.admin_id == user.id, Org.kind.in_(["ngo", "government"]))).first()
    if not org:
        raise HTTPException(403, "Only NGO or government organisations can read aggregate insights")
    return insights.aggregate(db)
