from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Appointment, CareMember, CheckIn, Consent, DoseLog, Document, Medicine, SymptomNote, User, Vital, now
from ..security import current_user, require_elder
from ..services import consent as C
from ..services import insights
from ..services.notify import local_time
from .health import _ci, _med, card_dict

router = APIRouter(tags=["family"])

PERIODS = {"daily": 1, "weekly": 7, "monthly": 30}


def build_report(db: Session, elder_id: int, period: str) -> dict:
    since = now() - timedelta(days=PERIODS.get(period, 7))
    cis = db.scalars(select(CheckIn).where(CheckIn.elder_id == elder_id, CheckIn.at >= since)).all()
    meds = db.scalars(select(Medicine).where(Medicine.elder_id == elder_id, Medicine.active)).all()
    expected = sum(len(m.times.split(",")) for m in meds) * PERIODS.get(period, 7)
    taken = db.scalar(select(func.count(DoseLog.id)).where(DoseLog.elder_id == elder_id, DoseLog.taken_at >= since)) or 0
    good = sum(1 for c in cis if c.mood == "good")
    return {"period": period, "checkins": len(cis), "good_days": good,
            "doses_taken": taken, "doses_expected": expected,
            "adherence_pct": round(100 * taken / expected) if expected else None,
            "good_news": insights.good_news(db, elder_id, PERIODS.get(period, 7))}


@router.get("/reports/{period}")
def my_report(period: str, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return build_report(db, user.id, period)


@router.get("/family/elders")
def my_elders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Elders who have shared at least one active item with me."""
    ids = {c.elder_id for c in db.scalars(select(Consent).where(Consent.grantee_id == user.id, Consent.revoked_at.is_(None))).all()
           if C._active(c)}
    ids |= {m.elder_id for m in db.scalars(select(CareMember).where(CareMember.member_id == user.id, CareMember.active)).all()}
    return [{"id": u.id, "name": u.name or u.phone, "local_time": local_time(u).strftime("%I:%M %p"), "timezone": u.timezone} for u in db.scalars(select(User).where(User.id.in_(ids))).all()] if ids else []


@router.get("/family/elders/{elder_id}/summary")
def summary(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Returns ONLY the sections the elder allowed. Each section read is written to the audit log."""
    out, hidden = {}, []

    def allowed(t):
        ok = C.has_consent(db, elder_id, user.id, t)
        if ok:
            C.log_access(db, elder_id, user.id, t)
        else:
            hidden.append(t)
        return ok

    if allowed("mood"):
        rows = db.scalars(select(CheckIn).where(CheckIn.elder_id == elder_id).order_by(CheckIn.id.desc()).limit(14)).all()
        out["mood"] = [{"at": c.at, "mood": c.mood} for c in rows]
    if allowed("checkin"):
        rows = db.scalars(select(CheckIn).where(CheckIn.elder_id == elder_id).order_by(CheckIn.id.desc()).limit(7)).all()
        out["checkins"] = [_ci(c) for c in rows]
    if allowed("medicines"):
        out["medicines"] = [_med(m) for m in db.scalars(select(Medicine).where(Medicine.elder_id == elder_id, Medicine.active)).all()]
    if allowed("vitals"):
        rows = db.scalars(select(Vital).where(Vital.elder_id == elder_id).order_by(Vital.id.desc()).limit(14)).all()
        out["vitals"] = [{"kind": v.kind, "value1": v.value1, "value2": v.value2, "flagged": v.flagged, "at": v.at} for v in rows]
    if allowed("emergency_card"):
        out["emergency_card"] = card_dict(db, elder_id)
    if allowed("reports"):
        out["report"] = build_report(db, elder_id, "weekly")
    if allowed("imfine"):
        last = db.scalars(select(CheckIn).where(CheckIn.elder_id == elder_id).order_by(CheckIn.id.desc())).first()
        out["imfine"] = bool(last and last.at >= now() - timedelta(days=1) and last.mood != "low")
    if allowed("appointments"):
        rows = db.scalars(select(Appointment).where(Appointment.elder_id == elder_id, Appointment.at >= now()).order_by(Appointment.at).limit(5)).all()
        out["appointments"] = [{"doctor": a.doctor, "at": a.at, "kind": a.kind} for a in rows]
    if allowed("symptoms"):
        rows = db.scalars(select(SymptomNote).where(SymptomNote.elder_id == elder_id).order_by(SymptomNote.id.desc()).limit(10)).all()
        out["symptoms"] = [{"at": r.at, "text": r.text} for r in rows]
    if allowed("documents"):
        rows = db.scalars(select(Document).where(Document.elder_id == elder_id).order_by(Document.id.desc()).limit(10)).all()
        out["documents"] = [{"id": d.id, "kind": d.kind, "title": d.title, "at": d.at} for d in rows]
    if allowed("activity"):
        out["activity"] = insights.activity_summary(db, elder_id)
    if allowed("cognitive"):
        from ..models import CognitiveResult
        rows = db.scalars(select(CognitiveResult).where(CognitiveResult.elder_id == elder_id).order_by(CognitiveResult.id.desc()).limit(6)).all()
        out["cognitive"] = [{"at": r.at, "score": r.score, "max": r.max_score} for r in rows]
    if "mood" in out:
        out["mood_trend"] = insights.mood_trend(db, elder_id)
    return {"shared": out, "not_shared": hidden}
