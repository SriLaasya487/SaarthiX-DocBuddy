from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import OtpCode, User, now
from ..security import current_user, hash_otp, make_otp, make_token, rate_limit
from ..services import kv

router = APIRouter(tags=["auth"])
ROLES = {"elder", "family", "doctor", "chw", "partner"}


class OtpReq(BaseModel):
    phone: str


class VerifyReq(BaseModel):
    phone: str
    otp: str
    name: str = ""
    role: str = "elder"
    language: str = "hi-IN"
    timezone: str = "Asia/Kolkata"


@router.post("/auth/request-otp")
def request_otp(body: OtpReq, request: Request, db: Session = Depends(get_db)):
    rate_limit(f"otp:{body.phone}", settings.otp_rate_per_hour)
    rate_limit(f"otp-ip:{request.client.host if request.client else '?'}", settings.otp_rate_per_hour * 5)
    db.execute(delete(OtpCode).where(OtpCode.phone == body.phone))
    code = make_otp()
    db.add(OtpCode(phone=body.phone, code_hash=hash_otp(body.phone, code), expires_at=now() + timedelta(seconds=settings.otp_ttl_seconds)))
    db.commit()
    from ..services.notify import _send
    user = db.scalars(select(User).where(User.phone == body.phone)).first() or User(phone=body.phone, name="", role="family")
    # OTP goes by SMS; for feature-phone elders the IVR provider reads it out loud.
    _send("ivr" if user.channel == "ivr" else "sms", user, f"Your DocBuddy code is {code}. Never share it with anyone.")
    return {"sent": True, **({"dev_otp": code} if settings.debug else {})}


@router.post("/auth/verify")
def verify(body: VerifyReq, db: Session = Depends(get_db)):
    otp = db.scalars(select(OtpCode).where(OtpCode.phone == body.phone)).first()
    if not otp or otp.expires_at < now():
        raise HTTPException(400, "Wrong or expired code")
    if otp.attempts >= settings.otp_max_attempts:
        db.delete(otp); db.commit()
        raise HTTPException(429, "Too many wrong codes. Please ask for a new one.")
    if otp.code_hash != hash_otp(body.phone, body.otp):
        otp.attempts += 1; db.commit()
        raise HTTPException(400, "Wrong or expired code")
    db.delete(otp)
    user = db.scalars(select(User).where(User.phone == body.phone)).first()
    if not user:
        role = body.role
        if role == "moderator" and body.phone in settings.admin_phones.split(","):
            pass
        elif role not in ROLES:
            raise HTTPException(400, "Bad role")
        user = User(phone=body.phone, name=body.name, role=role, language=body.language, timezone=body.timezone)
        db.add(user)
    elif body.name and not user.name:  # a placeholder created by someone's consent grant
        user.name = body.name
    db.commit()
    return {"token": make_token(user.id), "user": {"id": user.id, "name": user.name, "role": user.role, "language": user.language}}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"id": user.id, "name": user.name, "role": user.role, "language": user.language, "phone": user.phone,
            "timezone": user.timezone, "channel": user.channel, "settings": kv.settings_of(db, user.id) if user.role == "elder" else {}}


@router.patch("/me")
def update_me(body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for k in ("name", "language", "timezone"):
        if k in body:
            setattr(user, k, str(body[k]))
    if body.get("channel") in {"app", "ivr", "whatsapp", "sms"}:
        user.channel = body["channel"]
    db.commit()
    return {"ok": True}
