import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)


def make_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_otp(phone: str, code: str) -> str:
    return hashlib.sha256(f"{settings.jwt_secret}:{phone}:{code}".encode()).hexdigest()


def make_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.jwt_secret, algorithm="HS256")


_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(key: str, limit: int, per_seconds: int = 3600):
    """In-memory sliding window (use Redis when running several API replicas)."""
    q, t = _hits[key], time.monotonic()
    while q and q[0] < t - per_seconds:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many tries. Please wait a while.")
    q.append(t)


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not cred:
        raise HTTPException(401, "Not signed in")
    try:
        data = jwt.decode(cred.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = db.get(User, int(data["sub"]))
    if not user:
        raise HTTPException(401, "Unknown user")
    if db.bind.dialect.name == "postgresql":  # row-level security hook, see backend/sql/rls.sql
        db.execute(__import__("sqlalchemy").text("select set_config('app.user_id', :u, false)"), {"u": str(user.id)})
    return user


def require_elder(user: User = Depends(current_user)) -> User:
    if user.role != "elder":
        raise HTTPException(403, "Elder account required")
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, f"Requires role: {', '.join(roles)}")
        return user
    return dep


def device_elder(request: Request, db: Session = Depends(get_db)):
    """Auth for smart speakers / wearables / BLE gateways via a per-device token."""
    from .models import Device
    tok = request.headers.get("x-device-token", "")
    d = db.query(Device).filter(Device.token == tok).first() if tok else None
    if not d:
        raise HTTPException(401, "Unknown device")
    return d
