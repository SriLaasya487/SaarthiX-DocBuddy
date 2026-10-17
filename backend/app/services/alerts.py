from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Alert, User, now
from . import consent as C
from .notify import notify_user

# Which consent type governs who may be told about each alert kind.
TARGET_TYPE = {"sos": "sos", "fall": "sos", "help": "sos", "scam": "sos", "missed_dose": "sos",
               "low_mood": "mood", "cognitive": "cognitive"}


def dispatch(db: Session, alert: Alert) -> int:
    """Send ONLY to grantees holding an active 'escalate' consent for the relevant data type."""
    elder = db.get(User, alert.elder_id)
    targets = C.escalation_targets(db, alert.elder_id, TARGET_TYPE.get(alert.kind, "sos"))
    for uid in targets:
        notify_user(db, uid, f"[{alert.kind.upper()}] {elder.name}: {alert.message} {alert.location}".strip(), alert.elder_id)
    alert.status = "sent"
    db.commit()
    return len(targets)


def start_fall_countdown(db: Session, elder_id: int, location: str = "") -> Alert:
    a = Alert(elder_id=elder_id, kind="fall", message="A fall was detected and there was no answer.",
              location=location, auto_escalate_at=now() + timedelta(seconds=settings.fall_response_seconds))
    db.add(a); db.commit()
    return a


def ask_elder(db: Session, elder_id: int, kind: str, message: str) -> Alert:
    """Create an alert that waits for the elder's yes/no (principle 1)."""
    a = Alert(elder_id=elder_id, kind=kind, message=message)
    db.add(a); db.commit()
    return a


def process_expired(db: Session) -> int:
    """Called by the background loop: unanswered fall prompts escalate to pre-approved contacts only."""
    due = db.scalars(select(Alert).where(Alert.status == "pending_elder", Alert.auto_escalate_at.is_not(None),
                                         Alert.auto_escalate_at <= now())).all()
    for a in due:
        dispatch(db, a)
    return len(due)
