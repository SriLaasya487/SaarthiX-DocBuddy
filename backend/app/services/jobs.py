"""Background jobs run by the loop in main.py (use Celery/RQ beat in production). Each job is idempotent per day via a Kv marker."""
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Appointment, CallLog, CareMember, Consent, Medicine, Reminder, User, now
from . import alerts as A
from . import consent as C
from . import insights, kv
from .notify import local_time, notify_user


def _once(db: Session, elder_id: int, tag: str) -> bool:
    done = kv.get(db, elder_id, "jobs", {}) or {}
    if done.get(tag):
        return False
    done[tag] = str(now())
    for k in sorted(done)[:-60]:
        done.pop(k)
    kv.put(db, elder_id, "jobs", done)
    return True


def viewers(db: Session, elder_id: int, data_type: str) -> list[int]:
    return list({c.grantee_id for c in db.scalars(select(Consent).where(Consent.elder_id == elder_id, Consent.data_type == data_type, Consent.scope == "view",
                                                                       Consent.revoked_at.is_(None))).all() if C._active(c)})


def stock_alerts(db: Session) -> int:
    n = 0
    for m in db.scalars(select(Medicine).where(Medicine.active)).all():
        per_day = m.tablets * len(m.times.split(","))
        if m.stock <= per_day * 3 and _once(db, m.elder_id, f"stock:{m.id}:{date.today()}"):
            msg = f"{m.name} is running low: about {m.stock // max(1, per_day)} day(s) left."
            notify_user(db, m.elder_id, msg, m.elder_id)
            for v in viewers(db, m.elder_id, "medicines"):  # family sees it only because they already may see medicines
                notify_user(db, v, f"{db.get(User, m.elder_id).name}: {msg}", m.elder_id)
            n += 1
    return n


def appointment_reminders(db: Session) -> int:
    n = 0
    for a in db.scalars(select(Appointment).where(Appointment.at >= now(), Appointment.at <= now() + timedelta(hours=26))).all():
        stage = 2 if a.at - now() <= timedelta(hours=2) else 1 if a.at - now() <= timedelta(hours=25) else 0
        if stage > a.reminded:
            a.reminded = stage
            notify_user(db, a.elder_id, f"Reminder: visit with {a.doctor} at {a.at:%I:%M %p on %d %b}.", a.elder_id); n += 1
    db.commit()
    return n


def call_nudges(db: Session) -> int:
    n = 0
    for m in db.scalars(select(CareMember).where(CareMember.active, CareMember.role.in_(["primary", "sibling", "grandchild"]))).all():
        u = db.get(User, m.member_id)
        if local_time(u).hour != 18 or not _once(db, m.elder_id, f"callnudge:{m.member_id}:{date.today()}"):
            continue
        if not db.scalars(select(CallLog).where(CallLog.user_id == m.member_id, CallLog.elder_id == m.elder_id, CallLog.at >= now() - timedelta(hours=24))).first():
            notify_user(db, m.member_id, f"You have not called {db.get(User, m.elder_id).name} today. A short call means a lot.", m.elder_id); n += 1
    return n


def weekly_digest(db: Session) -> int:
    n = 0
    if date.today().weekday() != 6:
        return 0
    for e in db.scalars(select(User).where(User.role == "elder")).all():
        if not _once(db, e.id, f"digest:{date.today()}"):
            continue
        news = insights.good_news(db, e.id)
        if news:
            for v in viewers(db, e.id, "reports"):
                notify_user(db, v, f"Good news about {e.name}: " + " ".join(news), e.id); n += 1
    return n


def run_all(db: Session) -> dict:
    return {"expired_alerts": A.process_expired(db), "stock": stock_alerts(db), "appointments": appointment_reminders(db),
            "call_nudges": call_nudges(db), "digest": weekly_digest(db)}
