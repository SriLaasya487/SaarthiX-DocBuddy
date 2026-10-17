"""Doctor & records: symptom diary, pre-visit summary, post-visit notes, labs, locker, organiser, insurance, vaccines, check-ups,
tele-consult, recovery mode."""
import html
import json
import re
import secrets
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import (Appointment, CheckIn, Document, DoseLog, Medicine, PendingItem, Reminder, SymptomNote, User, Vital, now)
from ..security import current_user, require_elder
from ..services import consent as C
from ..services import content as K
from ..services import kv, rules
from ..services.pricing import gate

router = APIRouter(tags=["records"])


class TextReq(BaseModel):
    text: str


# ---------- symptom diary (DB-033) ----------
@router.post("/symptoms")
def add_symptom(body: TextReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    n = SymptomNote(elder_id=user.id, text=body.text); db.add(n); db.commit()
    return {"id": n.id}


@router.get("/symptoms")
def symptoms(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(SymptomNote).where(SymptomNote.elder_id == user.id).order_by(SymptomNote.id.desc()).limit(100)).all()
    return [{"id": r.id, "at": r.at, "text": r.text} for r in rows]


@router.delete("/symptoms/{sid}")
def del_symptom(sid: int, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    r = db.get(SymptomNote, sid)
    if not r or r.elder_id != user.id:
        raise HTTPException(404, "Not found")
    db.delete(r); db.commit()
    return {"ok": True}


# ---------- pre-visit summary (DB-038) ----------
def build_previsit(db: Session, elder_id: int, days: int = 30) -> dict:
    since = now() - timedelta(days=days)
    e = db.get(User, elder_id)
    meds = db.scalars(select(Medicine).where(Medicine.elder_id == elder_id, Medicine.active)).all()
    missed = []
    for m in meds:
        exp = len(m.times.split(",")) * days
        got = len(db.scalars(select(DoseLog).where(DoseLog.medicine_id == m.id, DoseLog.taken_at >= since)).all())
        if got < exp * 0.9:
            missed.append({"medicine": m.name, "missed_approx": exp - got, "of": exp})
    vit = db.scalars(select(Vital).where(Vital.elder_id == elder_id, Vital.at >= since).order_by(Vital.at)).all()
    notes = db.scalars(select(SymptomNote).where(SymptomNote.elder_id == elder_id, SymptomNote.at >= since).order_by(SymptomNote.at)).all()
    cis = db.scalars(select(CheckIn).where(CheckIn.elder_id == elder_id, CheckIn.at >= since)).all()
    qs = (kv.get(db, elder_id, "questions", []) or [])
    return {"patient": e.name, "period_days": days, "medicines": [{"name": m.name, "tablets": m.tablets, "times": m.times} for m in meds],
            "missed_doses": missed, "symptoms": [{"at": n.at.date().isoformat(), "text": n.text} for n in notes],
            "vitals": [{"at": v.at.date().isoformat(), "kind": v.kind, "value": f"{v.value1:g}" + (f"/{v.value2:g}" if v.value2 else ""), "flagged": v.flagged} for v in vit],
            "mood_low_days": sum(c.mood == "low" for c in cis), "pain_days": sum(c.pain != "none" for c in cis), "questions": qs,
            "disclaimer": "Prepared from what the patient recorded. It is not a diagnosis."}


@router.get("/previsit")
def previsit(days: int = 30, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return build_previsit(db, user.id, days)


class QuestionReq(BaseModel):
    question: str


@router.post("/previsit/questions")
def add_question(body: QuestionReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    q = kv.get(db, user.id, "questions", []) or []
    kv.put(db, user.id, "questions", q + [body.question][-20:])
    return {"questions": q + [body.question]}


def _previsit_html(p: dict) -> str:
    e = html.escape
    li = lambda xs: "".join(f"<li>{e(x)}</li>" for x in xs) or "<li>None</li>"
    return (f"<!doctype html><meta charset=utf-8><title>Pre-visit summary</title><style>body{{font:16px sans-serif;max-width:720px;margin:24px auto}}"
            f"h2{{border-bottom:1px solid #999}}.w{{color:#b00020}}</style><h1>Pre-visit summary: {e(p['patient'])}</h1><p>Last {p['period_days']} days</p>"
            f"<h2>Medicines</h2><ul>{li(m['name'] + ' x' + str(m['tablets']) + ' at ' + m['times'] for m in p['medicines'])}</ul>"
            f"<h2>Possibly missed doses</h2><ul>{li(m['medicine'] + ': about ' + str(m['missed_approx']) + ' of ' + str(m['of']) for m in p['missed_doses'])}</ul>"
            f"<h2>Symptoms (patient's words)</h2><ul>{li(s['at'] + ': ' + s['text'] for s in p['symptoms'])}</ul>"
            f"<h2>Readings</h2><ul>{li(v['at'] + ' ' + v['kind'].upper() + ' ' + v['value'] + (' (outside usual range)' if v['flagged'] else '') for v in p['vitals'])}</ul>"
            f"<h2>Questions for the doctor</h2><ul>{li(p['questions'])}</ul><p><i>{e(p['disclaimer'])}</i></p>")


@router.get("/previsit/print", response_class=HTMLResponse)
def previsit_print(days: int = 30, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return _previsit_html(build_previsit(db, user.id, days))


@router.get("/doctor/patients/{elder_id}/previsit")
def doctor_previsit(elder_id: int, days: int = 30, user: User = Depends(current_user), db: Session = Depends(get_db)):
    C.require_view(db, elder_id, user, "previsit")
    return build_previsit(db, elder_id, days)


# ---------- post-visit voice notes (DB-039) ----------
@router.post("/visit-notes")
def visit_note(body: TextReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    simple = rules.simplify_visit_note(body.text)
    p = PendingItem(elder_id=user.id, kind="visit_note", payload=json.dumps({"title": "Doctor's advice", "simple": simple, "original": body.text}),
                    readback=rules.readback("visit_note", {}))
    db.add(p); db.commit()
    lines = [*(f"Take: {x}" for x in simple["take"]), *(f"Avoid: {x}" for x in simple["avoid"]), *(f"Come back: {x}" for x in simple["follow_up"])]
    return {"pending_id": p.id, "simple": simple, "speak": "Here is what I understood. " + " ".join(lines) + " Shall I save this?"}


# ---------- documents: locker (DB-041), organiser (DB-070), labs (DB-040), insurance (DB-071) ----------
def _save_file(b64: str, ext: str = "bin") -> str:
    import base64
    d = Path(settings.media_dir); d.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{re.sub(r'[^a-z0-9]', '', ext.lower())[:5] or 'bin'}"
    (d / name).write_bytes(base64.b64decode(b64))
    return name


class DocIn(BaseModel):
    kind: str = "other"
    title: str
    text: str = ""
    expires_on: date | None = None
    file_b64: str = ""
    file_ext: str = "jpg"
    meta: dict = {}


KINDS = {"prescription", "report", "lab", "scan", "visit_note", "aadhaar", "pan", "insurance", "pension", "other"}


def _doc(d: Document, full=False):
    out = {"id": d.id, "kind": d.kind, "title": d.title, "expires_on": d.expires_on, "at": d.at, "has_file": bool(d.file_ref)}
    if full:
        out |= {"text": d.text, "meta": json.loads(d.meta or "{}")}
    return out


@router.post("/documents")
def add_doc(body: DocIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    if body.kind not in KINDS:
        raise HTTPException(400, "Unknown kind")
    if len(db.scalars(select(Document).where(Document.elder_id == user.id)).all()) >= 20:
        gate(db, user.id, "records_locker_unlimited")
    d = Document(elder_id=user.id, kind=body.kind, title=body.title, text=body.text, expires_on=body.expires_on, meta=json.dumps(body.meta),
                 file_ref=_save_file(body.file_b64, body.file_ext) if body.file_b64 else "")
    db.add(d); db.commit()
    if d.expires_on:  # expiry reminders 30 and 7 days before
        for n in (30, 7):
            if d.expires_on - timedelta(days=n) >= date.today():
                db.add(Reminder(elder_id=user.id, kind="document", title=f"{d.title} expires in {n} days", due_on=d.expires_on - timedelta(days=n)))
        db.commit()
    return _doc(d)


@router.get("/documents")
def docs(kind: str = "", user: User = Depends(require_elder), db: Session = Depends(get_db)):
    q = select(Document).where(Document.elder_id == user.id).order_by(Document.id.desc())
    return [_doc(d) for d in db.scalars(q).all() if not kind or d.kind == kind]


@router.get("/documents/expiring")
def expiring(days: int = 60, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(Document).where(Document.elder_id == user.id, Document.expires_on.is_not(None), Document.expires_on <= date.today() + timedelta(days=days))
                      .order_by(Document.expires_on)).all()
    return [{**_doc(d), "days_left": (d.expires_on - date.today()).days} for d in rows]


STOP = {"show", "my", "the", "me", "a", "last", "latest", "recent", "find", "open", "of", "report", "test", "please", "where", "is"}


@router.get("/documents/search")
def search(q: str, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Voice search: 'show my last sugar test' -> newest document/reading matching 'sugar'."""
    words = [w for w in re.findall(r"[a-z0-9]+", q.lower()) if w not in STOP]
    syn = {"sugar": ["sugar", "glucose", "hba1c", "diabetes"], "bp": ["bp", "pressure"], "xray": ["xray", "x-ray", "chest"], "mri": ["mri", "scan"], "blood": ["blood", "hemoglobin", "cbc"]}
    terms = {t for w in words for t in syn.get(w, [w])}
    docs_ = db.scalars(select(Document).where(Document.elder_id == user.id).order_by(Document.at.desc())).all()
    hit = [d for d in docs_ if any(t in f"{d.title} {d.kind} {d.text}".lower() for t in terms)]
    out = {"documents": [_doc(d) for d in (hit[:1] if re.search(r"\b(last|latest|recent)\b", q.lower()) else hit[:10])]}
    if terms & {"sugar", "glucose", "bp", "pressure", "pulse", "spo2", "oxygen"}:
        kind = "sugar" if terms & {"sugar", "glucose"} else "bp" if terms & {"bp", "pressure"} else "pulse" if "pulse" in terms else "spo2"
        v = db.scalars(select(Vital).where(Vital.elder_id == user.id, Vital.kind == kind).order_by(Vital.id.desc())).first()
        if v:
            out["reading"] = {"kind": v.kind, "value": f"{v.value1:g}" + (f"/{v.value2:g}" if v.value2 else ""), "at": v.at}
    first = out.get("reading") or (out["documents"][0] if out["documents"] else None)
    out["speak"] = (f"Your last {out['reading']['kind']} reading was {out['reading']['value']} on {out['reading']['at']:%d %b}." if "reading" in out
                    else f"I found {out['documents'][0]['title']}." if out["documents"] else "I could not find that. Try another word.")
    return out


@router.get("/documents/{did}")
def get_doc(did: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = db.get(Document, did)
    if not d:
        raise HTTPException(404, "Not found")
    C.require_view(db, d.elder_id, user, "labs" if d.kind == "lab" else "documents")
    return _doc(d, True)


@router.get("/documents/{did}/file")
def doc_file(did: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = db.get(Document, did)
    if not d or not d.file_ref:
        raise HTTPException(404, "Not found")
    C.require_view(db, d.elder_id, user, "documents")
    return Response((Path(settings.media_dir) / d.file_ref).read_bytes())


@router.delete("/documents/{did}")
def del_doc(did: int, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    d = db.get(Document, did)
    if not d or d.elder_id != user.id:
        raise HTTPException(404, "Not found")
    db.delete(d); db.commit()
    return {"ok": True}


@router.post("/labs/read")
def labs_read(body: TextReq, save: bool = False, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Plain-language explanation of lab values. Says where a value sits against the usual range, never what it means medically."""
    vals = rules.read_labs(body.text)
    res = {"values": vals, "speak": " ".join(v["say"] for v in vals) if vals else "I could not find known tests in this text.",
           "disclaimer": "DocBuddy cannot diagnose. Only your doctor can tell you what a result means. Labs print their own ranges - those matter most."}
    if save and vals:
        p = PendingItem(elder_id=user.id, kind="lab", payload=json.dumps({"title": "Lab report", "text": body.text, "values": vals}), readback="I read your lab report. Shall I save it?")
        db.add(p); db.commit(); res["pending_id"] = p.id
    return res


@router.get("/insurance")
def insurance(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(Document).where(Document.elder_id == user.id, Document.kind == "insurance").order_by(Document.expires_on)).all()
    return {"policies": [{**_doc(d), "days_to_renewal": (d.expires_on - date.today()).days if d.expires_on else None} for d in rows],
            "claim_steps": K.SAFE_CHECK_STEPS["claim"], "note": "General steps. Your insurer's policy document is the final word."}


# ---------- reminders: vaccination (DB-043), check-ups (DB-044), festivals/birthdays (DB-016) ----------
def _schedule(db, elder_id, key, catalogue):
    done = kv.get(db, elder_id, key, {}) or {}
    out = []
    for it in catalogue:
        last = date.fromisoformat(done[it["id"]]) if it["id"] in done else None
        nxt = rules.add_months(last, it["every_months"]) if last and it.get("every_months") else None
        out.append({**it, "last_done": last, "next_due": nxt, "overdue": bool(nxt and nxt < date.today()),
                    "say": f"{it['name']}: " + (f"last done {last:%d %b %Y}, next around {nxt:%b %Y}." if nxt else "Ask your doctor if and when you need it.")})
    return out


class DoneReq(BaseModel):
    id: str
    on: date | None = None


@router.get("/vaccinations")
def vaccinations(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return {"items": _schedule(db, user.id, "vaccines", K.VACCINES), "disclaimer": "This is a list to discuss with your doctor, not medical advice."}


@router.post("/vaccinations/done")
def vaccine_done(body: DoneReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    d = kv.get(db, user.id, "vaccines", {}) or {}
    d[body.id] = str(body.on or date.today()); kv.put(db, user.id, "vaccines", d)
    v = next((x for x in K.VACCINES if x["id"] == body.id), None)
    if v and v.get("every_months"):
        db.add(Reminder(elder_id=user.id, kind="vaccine", title=f"{v['name']} may be due - ask your doctor", due_on=rules.add_months(body.on or date.today(), v["every_months"])))
        db.commit()
    return {"ok": True}


@router.get("/checkups")
def checkups(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return {"items": _schedule(db, user.id, "checkups", K.CHECKUPS), "disclaimer": "Ask your doctor which of these you need and how often."}


@router.post("/checkups/done")
def checkup_done(body: DoneReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    d = kv.get(db, user.id, "checkups", {}) or {}
    d[body.id] = str(body.on or date.today()); kv.put(db, user.id, "checkups", d)
    c = next((x for x in K.CHECKUPS if x["id"] == body.id), None)
    if c:
        db.add(Reminder(elder_id=user.id, kind="checkup", title=f"{c['name']} is due", due_on=rules.add_months(body.on or date.today(), c["every_months"])))
        db.commit()
    return {"ok": True}


class ReminderIn(BaseModel):
    kind: str = "custom"  # birthday | festival | custom | alarm
    title: str
    due_on: date
    due_time: str = ""
    yearly: bool = False


@router.post("/reminders")
def add_reminder(body: ReminderIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    r = Reminder(elder_id=user.id, **body.model_dump()); db.add(r); db.commit()
    return {"id": r.id}


@router.get("/reminders/today")
def reminders_today(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Everything to announce today: festivals (built-in), birthdays, vaccines, check-ups, expiring papers, alarms. Spoken in the elder's language."""
    t = date.today()
    lang = (user.language or "en")[:2]
    out = []
    fest = K.FESTIVALS_FIXED.get(t.strftime("%m-%d")) or K.FESTIVALS_2026.get(str(t))
    if fest:
        out.append({"kind": "festival", "say": K.GREETING.get(lang, K.GREETING["en"]).format(f=fest)})
    for r in db.scalars(select(Reminder).where(Reminder.elder_id == user.id, Reminder.done.is_(False))).all():
        due = r.due_on.replace(year=t.year) if r.yearly else r.due_on
        if due == t or (r.kind in {"vaccine", "checkup", "document"} and r.due_on <= t):
            say = K.BIRTHDAY.get(lang, K.BIRTHDAY["en"]).format(n=r.title) if r.kind == "birthday" else r.title
            out.append({"kind": r.kind, "say": say, "id": r.id, "time": r.due_time})
    return out


@router.post("/reminders/{rid}/done")
def reminder_done(rid: int, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    r = db.get(Reminder, rid)
    if not r or r.elder_id != user.id:
        raise HTTPException(404, "Not found")
    r.done = True; db.commit()
    return {"ok": True}


# ---------- teleconsult (DB-042) ----------
class TeleReq(BaseModel):
    doctor: str = ""
    at: datetime
    note: str = ""


@router.post("/teleconsult/book")
def tele_book(body: TeleReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    gate(db, user.id, "teleconsult")
    fam = kv.settings_of(db, user.id).get("family_doctor_phone", "")
    a = Appointment(elder_id=user.id, doctor=body.doctor or "Family doctor", at=body.at, note=body.note, kind="tele",
                    join_url=f"https://meet.jit.si/docbuddy-tele-{secrets.token_urlsafe(8)}")
    db.add(a); db.commit()
    if fam:
        from ..services.notify import notify_user
        d = db.scalars(select(User).where(User.phone == fam)).first()
        if d:
            notify_user(db, d.id, f"{user.name} booked a video consult on {body.at:%d %b %I:%M %p}. Join: {a.join_url}", user.id)
    return {"id": a.id, "join_url": a.join_url}


@router.get("/teleconsult/join")
def tele_join(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """One-button join: the next tele appointment that is within 15 minutes before to 2 hours after its start."""
    a = db.scalars(select(Appointment).where(Appointment.elder_id == user.id, Appointment.kind == "tele", Appointment.at >= now() - timedelta(hours=2),
                                             Appointment.at <= now() + timedelta(minutes=15)).order_by(Appointment.at)).first()
    return {"join_url": a.join_url, "doctor": a.doctor} if a else {"join_url": "", "speak": "You have no video visit right now."}


# ---------- post-hospital recovery (DB-032) ----------
class RecoveryIn(BaseModel):
    title: str = "Recovery plan"
    items: list[str]          # copied from the discharge summary / doctor's instructions
    days: int = 14


@router.post("/recovery")
def recovery_create(body: RecoveryIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Items must come from the doctor/discharge summary (typed by elder or care team). DocBuddy adds none of its own medical items."""
    eid = user.id if user.role == "elder" else None
    if eid is None:
        raise HTTPException(403, "Ask the elder to confirm: use /consents/proposals style approval or create it from the elder's phone")
    plan = {"title": body.title, "items": [{"id": i, "text": t} for i, t in enumerate(body.items)], "ends": str(date.today() + timedelta(days=body.days)), "ticks": {}}
    kv.put(db, eid, "recovery", plan)
    return plan


@router.get("/recovery")
def recovery_get(elder_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    eid = user.id if user.role == "elder" else elder_id
    if user.role != "elder":
        C.require_view(db, eid, user, "recovery")
    plan = kv.get(db, eid, "recovery")
    if not plan or plan["ends"] < str(date.today()):
        return {"active": False}
    done = plan["ticks"].get(str(date.today()), [])
    return {"active": True, "title": plan["title"], "ends": plan["ends"], "today": [{**i, "done": i["id"] in done} for i in plan["items"]],
            "speak": f"{len(plan['items']) - len(done)} things left on your recovery list today."}


class TickReq(BaseModel):
    item_id: int


@router.post("/recovery/tick")
def recovery_tick(body: TickReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    plan = kv.get(db, user.id, "recovery")
    if not plan:
        raise HTTPException(404, "No plan")
    t = plan["ticks"].setdefault(str(date.today()), [])
    if body.item_id not in t:
        t.append(body.item_id)
    kv.put(db, user.id, "recovery", plan)
    return {"done": len(t), "total": len(plan["items"])}
