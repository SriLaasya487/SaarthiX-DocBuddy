"""The heart of DocBuddy: nothing leaves the elder without an active consent row."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AccessLog, CareMember, Consent, User, now

DATA_TYPES = {
    "mood": "your mood",
    "checkin": "your daily check-ins",
    "medicines": "your medicines and doses",
    "vitals": "your BP and sugar readings",
    "appointments": "your doctor visits",
    "reports": "your progress reports",
    "emergency_card": "your emergency card",
    "sos": "emergency alerts",
    "imfine": "your daily 'I am fine' message",
    "symptoms": "your symptom diary",
    "previsit": "your pre-visit summary",
    "documents": "your medical records and documents",
    "labs": "your lab reports",
    "activity": "your sleep and activity",
    "cognitive": "your memory check results",
    "life_story": "your life stories",
    "messages": "messages to you",
    "video": "video calls to you",
    "services": "help visits arranged for you",
    "recovery": "your recovery checklist",
}
SCOPES = {"view", "escalate", "send", "write"}

# Role -> default bundle PROPOSED to the elder. Nothing is granted until the elder approves.
ROLE_BUNDLES = {
    "primary": [(t, "view") for t in ("mood", "checkin", "medicines", "vitals", "appointments", "reports", "emergency_card",
                                       "imfine", "symptoms", "previsit", "documents", "activity", "recovery")]
               + [("sos", "escalate"), ("mood", "escalate"), ("video", "send"), ("messages", "send")],
    "sibling": [(t, "view") for t in ("reports", "imfine", "mood", "appointments")] + [("sos", "escalate"), ("messages", "send")],
    "doctor": [(t, "view") for t in ("vitals", "medicines", "symptoms", "labs", "previsit", "documents", "appointments",
                                      "emergency_card", "reports", "cognitive")],
    "neighbour": [("sos", "escalate"), ("emergency_card", "view")],
    "chw": [(t, "view") for t in ("checkin", "vitals", "medicines", "mood")] + [("vitals", "write"), ("checkin", "write")],
    "grandchild": [("messages", "send"), ("life_story", "view"), ("imfine", "view")],
    "guardian": [(t, "view") for t in ("medicines", "appointments", "emergency_card", "vitals", "reports", "documents")],
    "nominee": [],
}
# Nominee gets ONLY health-decision data when the incapacity process completes - never mood, stories or messages.
NOMINEE_BUNDLE = [(t, "view") for t in ("medicines", "appointments", "emergency_card", "vitals", "reports", "documents", "labs")]


def _active(c: Consent) -> bool:
    t = now()
    return c.revoked_at is None and (c.expires_at is None or c.expires_at > t)


def active_consent(db: Session, elder_id: int, grantee_id: int, data_type: str, scope: str = "view") -> Consent | None:
    rows = db.scalars(select(Consent).where(
        Consent.elder_id == elder_id, Consent.grantee_id == grantee_id,
        Consent.data_type == data_type, Consent.scope == scope)).all()
    return next((c for c in rows if _active(c)), None)


def has_consent(db: Session, elder_id: int, grantee_id: int, data_type: str, scope: str = "view") -> bool:
    return elder_id == grantee_id or active_consent(db, elder_id, grantee_id, data_type, scope) is not None


def log_access(db: Session, elder_id: int, actor_id: int, data_type: str, action: str = "view"):
    if elder_id != actor_id:
        db.add(AccessLog(elder_id=elder_id, actor_id=actor_id, data_type=data_type, action=action))
        db.commit()


def require_view(db: Session, elder_id: int, actor: User, data_type: str):
    """Raise 403 unless allowed; write audit entry when allowed."""
    if not has_consent(db, elder_id, actor.id, data_type):
        raise HTTPException(403, f"The elder has not shared {DATA_TYPES.get(data_type, data_type)} with you")
    log_access(db, elder_id, actor.id, data_type)


def require_scope(db: Session, elder_id: int, actor: User, data_type: str, scope: str):
    if not has_consent(db, elder_id, actor.id, data_type, scope):
        raise HTTPException(403, f"The elder has not allowed you to {scope} {DATA_TYPES.get(data_type, data_type)}")
    log_access(db, elder_id, actor.id, data_type, scope)


def grant(db: Session, elder_id: int, grantee_id: int, data_type: str, scope: str = "view", days: int | None = None) -> Consent:
    from datetime import timedelta
    if data_type not in DATA_TYPES or scope not in SCOPES:
        raise HTTPException(400, "Unknown data type or scope")
    exp = now() + timedelta(days=days) if days else None
    c = active_consent(db, elder_id, grantee_id, data_type, scope)
    if c:
        c.expires_at = exp
    else:
        c = Consent(elder_id=elder_id, grantee_id=grantee_id, data_type=data_type, scope=scope, expires_at=exp)
        db.add(c)
    db.commit()
    return c


def escalation_targets(db: Session, elder_id: int, data_type: str = "sos") -> list[int]:
    """Only people holding an active 'escalate' consent. Lowest priority number (e.g. trusted neighbour) first."""
    rows = db.scalars(select(Consent).where(
        Consent.elder_id == elder_id, Consent.data_type == data_type, Consent.scope == "escalate")).all()
    ids = [c.grantee_id for c in rows if _active(c)]
    prio = {m.member_id: m.priority for m in db.scalars(select(CareMember).where(CareMember.elder_id == elder_id)).all()}
    return sorted(set(ids), key=lambda i: prio.get(i, 5))


def is_team(db: Session, elder_id: int, user_id: int) -> bool:
    if elder_id == user_id:
        return True
    return db.scalars(select(CareMember).where(CareMember.elder_id == elder_id, CareMember.member_id == user_id,
                                               CareMember.active)).first() is not None


def team_role(db: Session, elder_id: int, user_id: int) -> str | None:
    m = db.scalars(select(CareMember).where(CareMember.elder_id == elder_id, CareMember.member_id == user_id,
                                            CareMember.active)).first()
    return m.role if m else None


def spoken_log(db: Session, elder_id: int, limit: int = 20) -> list[str]:
    """Plain-language answer to 'who saw what, and when?'"""
    logs = db.scalars(select(AccessLog).where(AccessLog.elder_id == elder_id)
                      .order_by(AccessLog.id.desc()).limit(limit)).all()
    out = []
    for l in logs:
        actor = db.get(User, l.actor_id)
        verb = {"view": "saw", "write": "added to", "send": "sent something using"}.get(l.action, l.action)
        out.append(f"{actor.name or actor.phone} {verb} {DATA_TYPES.get(l.data_type, l.data_type)} on {l.at:%d %b at %I:%M %p}.")
    return out or ["Nobody has seen your information yet."]
