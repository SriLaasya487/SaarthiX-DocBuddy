import json
from datetime import date, datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (Alert, Appointment, CheckIn, Document, DoseLog, DoseSnooze, EmergencyCard, Medicine, PendingItem, Refill,
                      Reminder, User, Vital, now)
from ..security import current_user, require_elder
from ..services import alerts as A
from ..services import consent as C
from ..services import kv, insights, rules
from ..services.doctor import suggest
from ..services.vitals import is_flagged

router = APIRouter(tags=["health"])


# ---------- medicines ----------
class MedIn(BaseModel):
    name: str
    tablets: int = 1
    times: str = "08:00"
    stock: int = 0
    missed_dose_note: str = ""
    color: str = ""
    generic_name: str = ""


def _med(m: Medicine):
    return {"id": m.id, "name": m.name, "tablets": m.tablets, "times": m.times.split(","), "stock": m.stock, "color": m.color,
            "low_stock": m.stock <= m.tablets * len(m.times.split(",")) * 3, "missed_dose_note": m.missed_dose_note,
            "days_left": m.stock // max(1, m.tablets * len(m.times.split(",")))}


@router.get("/medicines")
def list_meds(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return [_med(m) for m in db.scalars(select(Medicine).where(Medicine.elder_id == user.id, Medicine.active)).all()]


@router.post("/medicines")
def add_med(body: MedIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Manual entry. Scan / remote-setup results go through /pending and land here only after the elder confirms."""
    m = Medicine(elder_id=user.id, **body.model_dump())
    db.add(m); db.commit()
    return _med(m)


@router.delete("/medicines/{mid}")
def del_med(mid: int, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    m = db.get(Medicine, mid)
    if not m or m.elder_id != user.id:
        raise HTTPException(404, "Not found")
    m.active = False; db.commit()
    return {"ok": True}


GENTLE = ["It is time for {name}. {n} tablet{s}.", "A gentle reminder: {name} is still waiting.",
          "Please take {name} when you can. Shall I remind you again, or tell your family you need a hand?"]


@router.get("/medicines/due")
def due(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Slots whose time has arrived today, not confirmed and not snoozed. Wording gets softer-then-firmer with each snooze."""
    t = datetime.now()
    today = datetime(t.year, t.month, t.day)
    out = []
    for m in db.scalars(select(Medicine).where(Medicine.elder_id == user.id, Medicine.active)).all():
        for slot in m.times.split(","):
            h, mi = map(int, slot.split(":"))
            if (h, mi) > (t.hour, t.minute):
                continue
            if db.scalars(select(DoseLog).where(DoseLog.medicine_id == m.id, DoseLog.slot == slot, DoseLog.taken_at >= today)).first():
                continue
            sn = db.scalars(select(DoseSnooze).where(DoseSnooze.medicine_id == m.id, DoseSnooze.slot == slot, DoseSnooze.day == str(today.date()))).first()
            if sn and sn.until > now():
                continue
            c = sn.count if sn else 0
            out.append({"medicine_id": m.id, "name": m.name, "tablets": m.tablets, "slot": slot, "snoozed": c,
                        "speak": GENTLE[min(c, 2)].format(name=m.name, n=m.tablets, s="s" if m.tablets != 1 else ""),
                        "offer_tell_family": c >= 2, "missed_dose_note": m.missed_dose_note})
    return out


class TakenReq(BaseModel):
    slot: str


@router.post("/medicines/{mid}/taken")
def taken(mid: int, body: TakenReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    m = db.get(Medicine, mid)
    if not m or m.elder_id != user.id:
        raise HTTPException(404, "Not found")
    db.add(DoseLog(medicine_id=mid, elder_id=user.id, slot=body.slot))
    m.stock = max(0, m.stock - m.tablets)
    db.commit()
    return _med(m)


class SnoozeReq(BaseModel):
    slot: str
    minutes: int = 10


@router.post("/medicines/{mid}/snooze")
def snooze(mid: int, body: SnoozeReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    m = db.get(Medicine, mid)
    if not m or m.elder_id != user.id:
        raise HTTPException(404, "Not found")
    day = str(date.today())
    s = db.scalars(select(DoseSnooze).where(DoseSnooze.medicine_id == mid, DoseSnooze.slot == body.slot, DoseSnooze.day == day)).first()
    if s:
        s.count += 1; s.until = now() + timedelta(minutes=body.minutes)
    else:
        s = DoseSnooze(medicine_id=mid, elder_id=user.id, slot=body.slot, day=day, until=now() + timedelta(minutes=body.minutes))
        db.add(s)
    db.commit()
    return {"snoozed": s.count, "until": s.until, "offer_tell_family": s.count >= 3}


@router.post("/medicines/{mid}/missed")
def missed(mid: int, body: TakenReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """'I missed a dose': show ONLY the doctor-approved instruction. If none exists, say so - never improvise."""
    m = db.get(Medicine, mid)
    if not m or m.elder_id != user.id:
        raise HTTPException(404, "Not found")
    if m.missed_dose_note.strip():
        return {"speak": f"Your doctor's instruction for {m.name}: {m.missed_dose_note}", "doctor_approved": True}
    return {"speak": f"I do not have your doctor's instruction for a missed {m.name}. Please do not double the dose. Ask your doctor or pharmacist.",
            "doctor_approved": False}


class VerifyPillbox(BaseModel):
    counts: dict[str, int]  # colour -> number of tablets seen in the photo (detected on the phone)
    slot: str = ""


@router.post("/pillbox/verify")
def pillbox_verify(body: VerifyPillbox, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Compare what the photo shows (count + colour) with what is scheduled. Reports mismatches; never decides what to take."""
    exp: dict[str, int] = {}
    unknown = 0
    for m in db.scalars(select(Medicine).where(Medicine.elder_id == user.id, Medicine.active)).all():
        slots = [s for s in m.times.split(",") if not body.slot or s == body.slot]
        if not slots:
            continue
        if m.color:
            exp[m.color.lower()] = exp.get(m.color.lower(), 0) + m.tablets * (1 if body.slot else len(slots))
        else:
            unknown += m.tablets * (1 if body.slot else len(slots))
    seen = {k.lower(): v for k, v in body.counts.items()}
    issues = []
    for c in sorted(set(exp) | set(seen)):
        if seen.get(c, 0) < exp.get(c, 0): issues.append(f"{exp[c] - seen.get(c, 0)} {c} tablet(s) missing")
        if seen.get(c, 0) > exp.get(c, 0) and (c in exp or not unknown): issues.append(f"{seen[c] - exp.get(c, 0)} extra {c} tablet(s)")
    ok = not issues
    return {"ok": ok, "issues": issues, "expected": exp, "unlabelled_tablets_expected": unknown,
            "speak": "The tablets match your schedule." if ok else "Something looks different: " + "; ".join(issues) + ". Please check with your family or pharmacist before taking.",
            "note": "Photo checks can be wrong. When in doubt, ask."}


# ---------- refills & pharmacy ----------
class RefillReq(BaseModel):
    medicine_id: int
    channel: str = "whatsapp"  # 1mg | pharmeasy | whatsapp


@router.post("/refills")
def refill(body: RefillReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    m = db.get(Medicine, body.medicine_id)
    if not m or m.elder_id != user.id:
        raise HTTPException(404, "Not found")
    r = Refill(elder_id=user.id, medicine_id=m.id, channel=body.channel)
    db.add(r); db.commit()
    return {"id": r.id, "status": r.status, "speak": f"Shall I ask the pharmacy for more {m.name}?"}


@router.post("/refills/{rid}/confirm")
def refill_confirm(rid: int, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    r = db.get(Refill, rid)
    if not r or r.elder_id != user.id:
        raise HTTPException(404, "Not found")
    m = db.get(Medicine, r.medicine_id)
    text = f"Namaste, please send {m.name} ({m.tablets * len(m.times.split(','))} per day, about 30 days) to {user.name}."
    ph = "".join(ch for ch in kv.settings_of(db, user.id).get("pharmacy_phone", "") if ch.isdigit())
    r.link = (f"https://wa.me/{ph}?text={quote(text)}" if r.channel == "whatsapp" and ph else
              f"https://www.1mg.com/search/all?name={quote(m.name)}" if r.channel == "1mg" else
              f"https://pharmeasy.in/search/all?name={quote(m.name)}" if r.channel == "pharmeasy" else "")
    r.status = "confirmed"; db.commit()
    return {"status": r.status, "open": r.link, "note": "Payment and delivery happen with the pharmacy, not inside DocBuddy." if r.link else "Add your pharmacy's WhatsApp number in Settings."}


# ---------- prescription scan / interactions / generics ----------
class TextReq(BaseModel):
    text: str


@router.post("/prescriptions/parse")
def parse_rx(body: TextReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """OCR text (from the phone or server OCR) -> CANDIDATES waiting in /pending. Nothing is saved to the medicine list yet."""
    items = rules.parse_prescription(body.text)
    out = []
    for it in items:
        p = PendingItem(elder_id=user.id, kind="medicine", payload=json.dumps({k: v for k, v in it.items() if k != "source_line"}),
                        readback=rules.readback("medicine", it))
        db.add(p); db.flush(); out.append({"pending_id": p.id, **it, "readback": p.readback})
    db.commit()
    return {"candidates": out, "note": "Please check each line against your paper prescription and confirm."}


class ImageReq(BaseModel):
    image_b64: str


@router.post("/prescriptions/scan")
def scan_rx(body: ImageReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Server-side OCR if pytesseract is installed; otherwise the app runs OCR on the phone and calls /prescriptions/parse."""
    try:
        import base64, io
        import pytesseract
        from PIL import Image
        text = pytesseract.image_to_string(Image.open(io.BytesIO(base64.b64decode(body.image_b64))))
    except ImportError:
        raise HTTPException(501, "Server OCR is not installed. The app reads the photo on the phone and sends the text to /prescriptions/parse.")
    return parse_rx(TextReq(text=text), user, db)


@router.get("/medicines/interactions")
def med_interactions(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    names = [m.name for m in db.scalars(select(Medicine).where(Medicine.elder_id == user.id, Medicine.active)).all()]
    found = rules.interactions(names)
    return {"found": found, "speak": ("Some of your medicines may need a check: " + " ".join(f['note'] for f in found) + " Please ask your doctor or pharmacist.") if found
            else "I did not find anything in my short list. That does not mean there is no issue. Ask your pharmacist when you buy new medicines.",
            "disclaimer": "Information only. DocBuddy cannot tell you to stop or change any medicine."}


@router.get("/medicines/generic/{name}")
def generic(name: str, user: User = Depends(require_elder)):
    return rules.generic_info(name)


# ---------- pending confirmation (principle 4) + voice read-back (DB-012) ----------
@router.get("/pending")
def pending(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(PendingItem).where(PendingItem.elder_id == user.id, PendingItem.status == "pending").order_by(PendingItem.id)).all()
    return [{"id": p.id, "kind": p.kind, "payload": json.loads(p.payload), "readback": p.readback or rules.readback(p.kind, json.loads(p.payload)),
             "proposed_by": (db.get(User, p.proposed_by).name if p.proposed_by else None)} for p in rows]


class PendingIn(BaseModel):
    kind: str
    payload: dict


@router.post("/pending")
def pending_add(body: PendingIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    if body.kind not in {"medicine", "vital", "visit_note", "appointment", "lab"}:
        raise HTTPException(400, "Unknown kind")
    p = PendingItem(elder_id=user.id, kind=body.kind, payload=json.dumps(body.payload), readback=rules.readback(body.kind, body.payload))
    db.add(p); db.commit()
    return {"id": p.id, "readback": p.readback}


def apply_pending(db: Session, p: PendingItem, elder: User) -> dict:
    d = json.loads(p.payload)
    if p.kind == "medicine":
        m = Medicine(elder_id=elder.id, name=d["name"], tablets=int(d.get("tablets", 1)), times=d.get("times", "08:00"), stock=int(d.get("stock", 0)),
                     missed_dose_note=d.get("missed_dose_note", ""), color=d.get("color", ""))
        db.add(m); db.flush(); return {"medicine_id": m.id}
    if p.kind == "vital":
        v = Vital(elder_id=elder.id, kind=d["kind"], value1=d["value1"], value2=d.get("value2"), flagged=is_flagged(d["kind"], d["value1"], d.get("value2")),
                  source=d.get("source", "voice"))
        db.add(v); db.flush()
        return {"vital_id": v.id, "flagged": v.flagged, "advice": "This reading is outside the usual range. Please tell your doctor." if v.flagged else ""}
    if p.kind == "appointment":
        a = Appointment(elder_id=elder.id, doctor=d["doctor"], at=datetime.fromisoformat(d["at"]), note=d.get("note", ""))
        db.add(a); db.flush(); return {"appointment_id": a.id}
    if p.kind == "visit_note":
        doc = Document(elder_id=elder.id, kind="visit_note", title=d.get("title", "Doctor's advice"), text=json.dumps(d.get("simple", d)))
        db.add(doc); db.flush()
        days = (d.get("simple") or {}).get("follow_up_in_days")
        if days:
            db.add(Reminder(elder_id=elder.id, kind="custom", title="Follow-up visit with your doctor", due_on=date.today() + timedelta(days=days)))
        return {"document_id": doc.id}
    if p.kind == "lab":
        doc = Document(elder_id=elder.id, kind="lab", title=d.get("title", "Lab report"), text=d.get("text", ""), meta=json.dumps(d.get("values", [])))
        db.add(doc); db.flush(); return {"document_id": doc.id}
    return {}


class ConfirmReq(BaseModel):
    confirm: bool = True
    edits: dict | None = None  # elder corrected a field before saving


@router.post("/pending/{pid}")
def pending_decide(pid: int, body: ConfirmReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    p = db.get(PendingItem, pid)
    if not p or p.elder_id != user.id or p.status != "pending":
        raise HTTPException(404, "Not found")
    if not body.confirm:
        p.status = "rejected"; db.commit()
        return {"status": "rejected"}
    if body.edits:
        p.payload = json.dumps({**json.loads(p.payload), **body.edits})
    res = apply_pending(db, p, user)
    p.status = "confirmed"; db.commit()
    return {"status": "confirmed", **res}


# ---------- check-in ----------
class CheckInIn(BaseModel):
    mood: str  # good | okay | low
    pain: str = "none"
    took_medicines: bool = True
    needs_help: bool = False
    doctor_visit_soon: bool = False
    note: str = ""


@router.post("/checkin")
def checkin(body: CheckInIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    c = CheckIn(elder_id=user.id, **body.model_dump())
    db.add(c)
    asked = None
    if body.needs_help or body.pain == "strong":
        a = A.ask_elder(db, user.id, "help", "Needs help." if body.needs_help else "Reported strong pain.")  # ask the elder first
        asked = a.id
    db.commit()
    pats = insights.patterns(db, user.id)
    trend = insights.mood_trend(db, user.id)
    low_alert = None
    if trend["persistent_low"]:  # mood trend over weeks: ask the elder before telling anyone
        open_ = db.scalars(select(Alert).where(Alert.elder_id == user.id, Alert.kind == "low_mood", Alert.status == "pending_elder")).first()
        low_alert = (open_ or A.ask_elder(db, user.id, "low_mood", "Has felt low for several weeks and may like a call.")).id
    return {"id": c.id, "ask_to_inform_family_alert_id": asked, "ask_low_mood_alert_id": low_alert,
            "pattern_note": ("You have felt low a few days in a row. Would you like to talk to someone?" if any("low" in p for p in pats) else (pats[0] if pats else "")),
            "patterns": pats}


@router.get("/checkin")
def my_checkins(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(CheckIn).where(CheckIn.elder_id == user.id).order_by(CheckIn.id.desc()).limit(30)).all()
    return [_ci(c) for c in rows]


def _ci(c: CheckIn):
    return {"at": c.at, "mood": c.mood, "pain": c.pain, "took_medicines": c.took_medicines, "needs_help": c.needs_help, "note": c.note}


# ---------- doctor suggestion ----------
class SymptomReq(BaseModel):
    symptom: str


@router.post("/doctor/suggest")
def doctor_suggest(body: SymptomReq, user: User = Depends(require_elder)):
    return suggest(body.symptom)


# ---------- vitals ----------
class VitalIn(BaseModel):
    kind: str
    value1: float
    value2: float | None = None
    source: str = "manual"


@router.post("/vitals")
def add_vital(body: VitalIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    if body.kind not in {"bp", "sugar", "spo2", "pulse"}:
        raise HTTPException(400, "Unknown vital")
    v = Vital(elder_id=user.id, flagged=is_flagged(body.kind, body.value1, body.value2), **body.model_dump())
    db.add(v); db.commit()
    return {"id": v.id, "flagged": v.flagged, "advice": "This reading is outside the usual range. Please tell your doctor." if v.flagged else ""}


@router.post("/vitals/voice")
def vital_voice(body: TextReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """'BP is 140 over 90' -> read back and wait for 'yes' (POST /pending/{id}) before anything is stored."""
    v = rules.parse_vital(body.text)
    if not v:
        return {"understood": False, "speak": "I could not find a reading. Please say, for example: B P is 140 over 90."}
    p = PendingItem(elder_id=user.id, kind="vital", payload=json.dumps({**v, "source": "voice"}), readback=rules.readback("vital", v))
    db.add(p); db.commit()
    return {"understood": True, "pending_id": p.id, "speak": p.readback}


@router.get("/vitals")
def vitals(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(Vital).where(Vital.elder_id == user.id).order_by(Vital.id.desc()).limit(60)).all()
    return [{"kind": v.kind, "value1": v.value1, "value2": v.value2, "flagged": v.flagged, "at": v.at, "source": v.source} for v in rows]


# ---------- appointments ----------
class ApptIn(BaseModel):
    doctor: str
    at: datetime
    note: str = ""
    kind: str = "visit"


@router.post("/appointments")
def add_appt(body: ApptIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    a = Appointment(elder_id=user.id, **body.model_dump()); db.add(a); db.commit()
    return {"id": a.id}


@router.get("/appointments")
def appts(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(Appointment).where(Appointment.elder_id == user.id, Appointment.at >= now()).order_by(Appointment.at)).all()
    return [{"id": a.id, "doctor": a.doctor, "at": a.at, "note": a.note, "kind": a.kind, "join_url": a.join_url} for a in rows]


@router.get("/appointments/due")
def appts_due(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Spoken + large on-screen reminders for visits in the next 24 hours."""
    rows = db.scalars(select(Appointment).where(Appointment.elder_id == user.id, Appointment.at >= now(), Appointment.at <= now() + timedelta(hours=24))
                      .order_by(Appointment.at)).all()
    return [{"id": a.id, "doctor": a.doctor, "at": a.at, "in_minutes": int((a.at - now()).total_seconds() // 60),
             "speak": f"Reminder: you have a visit with {a.doctor} at {a.at:%I:%M %p}" + (" today." if a.at.date() == date.today() else " tomorrow.")} for a in rows]


# ---------- emergency card ----------
class CardIn(BaseModel):
    blood_group: str = ""
    allergies: str = ""
    doctor_phone: str = ""
    doctor_name: str = ""
    conditions: str = ""
    contacts: str = ""


@router.put("/emergency-card")
def put_card(body: CardIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    c = db.get(EmergencyCard, user.id) or EmergencyCard(elder_id=user.id)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.add(c); db.commit()
    return {"ok": True}


def card_dict(db: Session, elder_id: int):
    c = db.get(EmergencyCard, elder_id)
    meds = [m.name for m in db.scalars(select(Medicine).where(Medicine.elder_id == elder_id, Medicine.active)).all()]
    g = lambda k: getattr(c, k) if c else ""
    return {"blood_group": g("blood_group"), "allergies": g("allergies"), "doctor_phone": g("doctor_phone"), "doctor_name": g("doctor_name"),
            "conditions": g("conditions"), "contacts": g("contacts"), "medicines": meds}


@router.get("/emergency-card")
def get_card(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return card_dict(db, user.id)


@router.get("/emergency-card/print", response_class=HTMLResponse)
def card_print(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    import html
    c = card_dict(db, user.id)
    row = lambda k, v: f"<tr><th>{k}</th><td>{html.escape(', '.join(v) if isinstance(v, list) else str(v) or '-')}</td></tr>"
    return (f"<!doctype html><meta charset=utf-8><title>Emergency card</title><style>body{{font:22px sans-serif;max-width:600px;margin:20px auto}}"
            f"th{{text-align:left;padding:6px 14px 6px 0}}h1{{color:#b00020}}</style><h1>EMERGENCY CARD</h1><h2>{html.escape(user.name)}</h2><table>"
            + row("Blood group", c["blood_group"]) + row("Allergies", c["allergies"]) + row("Conditions", c["conditions"]) + row("Medicines", c["medicines"])
            + row("Doctor", f"{c['doctor_name']} {c['doctor_phone']}") + row("Contacts", c["contacts"]) + "</table><p>Ambulance 108 · Emergency 112</p>")
