import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CareMember, Consent, ConsentProposal, User, now
from ..security import current_user, require_elder
from ..services import consent as C
from ..services import kv
from ..services.rules import parse_revoke

router = APIRouter(prefix="/consents", tags=["consent"])


class GrantReq(BaseModel):
    grantee_phone: str
    grantee_name: str = ""
    data_type: str
    scope: str = "view"
    days: int | None = None  # temporary sharing, e.g. 7 days for a doctor
    relation: str = ""


def _row(db, c: Consent):
    g = db.get(User, c.grantee_id)
    rel = (kv.get(db, c.elder_id, "relations", {}) or {}).get(str(g.id), "")
    return {"id": c.id, "grantee": g.name or g.phone, "grantee_id": g.id, "role": g.role, "relation": rel, "data_type": c.data_type,
            "scope": c.scope, "expires_at": c.expires_at, "revoked": c.revoked_at is not None}


def _grantee(db, phone, name="", role="family") -> User:
    g = db.scalars(select(User).where(User.phone == phone)).first()
    if not g:  # placeholder so the family member can sign in later with this number
        g = User(phone=phone, name=name, role=role); db.add(g); db.commit()
    return g


def set_relation(db, elder_id, grantee_id, relation):
    if relation:
        rel = kv.get(db, elder_id, "relations", {}) or {}
        rel[str(grantee_id)] = relation.lower()
        kv.put(db, elder_id, "relations", rel)


@router.get("/types")
def types():
    return C.DATA_TYPES


@router.get("")
def my_grants(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(Consent).where(Consent.elder_id == user.id, Consent.revoked_at.is_(None))).all()
    return [_row(db, c) for c in rows if C._active(c)]


@router.post("")
def grant(body: GrantReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    if body.data_type not in C.DATA_TYPES or body.scope not in C.SCOPES:
        raise HTTPException(400, "Unknown data type or scope")
    g = _grantee(db, body.grantee_phone, body.grantee_name)
    c = C.grant(db, user.id, g.id, body.data_type, body.scope, body.days)
    set_relation(db, user.id, g.id, body.relation)
    return _row(db, c)


class DoctorShare(BaseModel):
    doctor_phone: str
    doctor_name: str = ""
    days: int = 7


@router.post("/share-with-doctor")
def share_with_doctor(body: DoctorShare, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Temporary sharing: the pre-visit bundle for N days (default 7), then it ends by itself."""
    g = _grantee(db, body.doctor_phone, body.doctor_name, "doctor")
    for t in ("previsit", "vitals", "medicines", "symptoms", "labs", "emergency_card"):
        C.grant(db, user.id, g.id, t, "view", body.days)
    return {"shared_with": g.name or g.phone, "days": body.days, "types": ["previsit", "vitals", "medicines", "symptoms", "labs", "emergency_card"]}


@router.delete("/{cid}")
def revoke(cid: int, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    c = db.get(Consent, cid)
    if not c or c.elder_id != user.id:
        raise HTTPException(404, "Not found")
    c.revoked_at = now(); db.commit()
    return {"revoked": True}


@router.post("/revoke-all/{grantee_id}")
def revoke_all(grantee_id: int, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(Consent).where(Consent.elder_id == user.id, Consent.grantee_id == grantee_id, Consent.revoked_at.is_(None))).all()
    for c in rows:
        c.revoked_at = now()
    db.commit()
    return {"revoked": len(rows)}


class VoiceRevoke(BaseModel):
    text: str  # "Stop sharing my mood with my son"


@router.post("/revoke-by-voice")
def revoke_by_voice(body: VoiceRevoke, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    p = parse_revoke(body.text)
    rels = kv.get(db, user.id, "relations", {}) or {}
    rows = db.scalars(select(Consent).where(Consent.elder_id == user.id, Consent.revoked_at.is_(None))).all()
    rows = [c for c in rows if C._active(c)]
    t = body.text.lower()

    def who(c):
        g = db.get(User, c.grantee_id)
        names = [(g.name or "").lower(), rels.get(str(g.id), ""), g.role]
        return any(n and n in t for n in names) or (p["relation"] and p["relation"] in names)

    hits = [c for c in rows if who(c) and (p["everything"] or c.data_type in p["types"])]
    if not hits:
        return {"revoked": 0, "speak": "I could not find who you mean. Please say the name and what to stop sharing."}
    for c in hits:
        c.revoked_at = now()
    db.commit()
    g = db.get(User, hits[0].grantee_id)
    what = "everything" if p["everything"] else ", ".join(C.DATA_TYPES[x] for x in p["types"])
    return {"revoked": len(hits), "speak": f"Done. I stopped sharing {what} with {g.name or g.phone}."}


@router.get("/log")
def log(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """'Who saw what, and when?' - returned as ready-to-speak sentences."""
    return {"sentences": C.spoken_log(db, user.id)}


# ---------- caregiver-assisted setup: proposals the elder approves by voice or button ----------
@router.get("/proposals")
def proposals(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(ConsentProposal).where(ConsentProposal.elder_id == user.id, ConsentProposal.status == "pending")).all()
    out = []
    for p in rows:
        g, pr = db.get(User, p.grantee_id), db.get(User, p.proposer_id)
        items = json.loads(p.items)
        out.append({"id": p.id, "proposed_by": pr.name or pr.phone, "grantee": g.name or g.phone, "role": p.role, "days": p.days,
                    "items": items, "speak": f"{pr.name or pr.phone} would like you to share {', '.join(C.DATA_TYPES[i['data_type']] for i in items)} with {g.name or g.phone}. Do you agree?"})
    return out


class Decide(BaseModel):
    approve: bool


@router.post("/proposals/{pid}")
def decide(pid: int, body: Decide, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    p = db.get(ConsentProposal, pid)
    if not p or p.elder_id != user.id or p.status != "pending":
        raise HTTPException(404, "Not found")
    if not body.approve:
        p.status = "declined"; db.commit()
        return {"status": "declined"}
    for it in json.loads(p.items):
        C.grant(db, user.id, p.grantee_id, it["data_type"], it["scope"], p.days)
    set_relation(db, user.id, p.grantee_id, p.relation)
    if p.role:
        m = db.scalars(select(CareMember).where(CareMember.elder_id == user.id, CareMember.member_id == p.grantee_id)).first()
        if m:
            m.role, m.active = p.role, True
        else:
            db.add(CareMember(elder_id=user.id, member_id=p.grantee_id, role=p.role, relation=p.relation,
                              priority=1 if p.role == "neighbour" else 5))
    p.status = "approved"; db.commit()
    return {"status": "approved"}
