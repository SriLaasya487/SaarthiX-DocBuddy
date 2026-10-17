from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Alert, User
from ..security import require_elder
from ..services import alerts as A
from .health import card_dict

router = APIRouter(tags=["safety"])


class SosReq(BaseModel):
    location: str = ""  # "lat,lng"


@router.post("/sos")
def sos(body: SosReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Pressing SOS is itself the elder's consent. Still only goes to contacts they pre-approved for 'sos'."""
    a = Alert(elder_id=user.id, kind="sos", message=f"SOS! Emergency card: {card_dict(db, user.id)}", location=body.location)
    db.add(a); db.commit()
    n = A.dispatch(db, a)
    return {"alert_id": a.id, "contacts_notified": n, "call_112_hint": True}


@router.post("/fall")
def fall(body: SosReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Phone detected a fall -> app asks 'Are you okay?'. No answer within the window escalates (approved contacts only)."""
    a = A.start_fall_countdown(db, user.id, body.location)
    return {"alert_id": a.id, "respond_before": a.auto_escalate_at}


class RespondReq(BaseModel):
    allow: bool


@router.post("/alerts/{aid}/respond")
def respond(aid: int, body: RespondReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Elder answers 'Shall I tell your family?' (help/pain) or 'Are you okay?' (fall: allow=False means 'I am fine')."""
    a = db.get(Alert, aid)
    if not a or a.elder_id != user.id:
        raise HTTPException(404, "Not found")
    if a.status != "pending_elder":
        return {"status": a.status}
    if body.allow:
        n = A.dispatch(db, a)
        return {"status": "sent", "contacts_notified": n}
    a.status = "declined" if a.kind != "fall" else "cancelled"
    db.commit()
    return {"status": a.status}


@router.get("/alerts")
def my_alerts(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(Alert).where(Alert.elder_id == user.id).order_by(Alert.id.desc()).limit(20)).all()
    return [{"id": a.id, "kind": a.kind, "status": a.status, "message": a.message, "created_at": a.created_at} for a in rows]
