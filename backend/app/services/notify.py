"""Notification hub: outbox row + best-effort delivery on the person's preferred channel.
Channels: whatsapp (WhatsApp Business Cloud API), sms (generic HTTP gateway), push (FCM), ivr (voice call), log.
Without credentials nothing leaves the server - the message is stored in the outbox and logged."""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Notification, User, now
from . import kv

log = logging.getLogger("docbuddy.notify")
URGENT = ("SOS", "FALL", "HELP", "SCAM")


def local_time(user: User, when: datetime | None = None) -> datetime:
    """NRI mode: show times in the RECIPIENT's time zone."""
    utc = (when or now()).replace(tzinfo=ZoneInfo("UTC"))
    try:
        return utc.astimezone(ZoneInfo(user.timezone or "Asia/Kolkata"))
    except Exception:
        return utc


def _quiet(db: Session, user: User, urgent: bool) -> bool:
    if urgent:
        return False
    qh = kv.settings_of(db, user.id).get("quiet_hours") or [22, 6]
    h = local_time(user).hour
    return h >= qh[0] or h < qh[1]


def _send(channel: str, user: User, text: str) -> bool:
    try:
        if channel == "whatsapp" and settings.whatsapp_token and settings.whatsapp_phone_id:
            r = httpx.post(f"https://graph.facebook.com/v20.0/{settings.whatsapp_phone_id}/messages", timeout=8,
                           headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
                           json={"messaging_product": "whatsapp", "to": user.phone, "type": "template",
                                 "template": {"name": settings.whatsapp_template, "language": {"code": "en"},
                                              "components": [{"type": "body", "parameters": [{"type": "text", "text": text[:900]}]}]}})
            return r.is_success
        if channel == "sms" and settings.sms_url:
            r = httpx.post(settings.sms_url, timeout=8, headers={"Authorization": f"Bearer {settings.sms_key}"},
                           json={"to": user.phone, "sender": settings.sms_sender, "text": text[:600]})
            return r.is_success
        if channel == "ivr" and settings.ivr_provider_url:
            r = httpx.post(settings.ivr_provider_url, timeout=8, headers={"Authorization": f"Bearer {settings.ivr_provider_key}"},
                           json={"to": user.phone, "say": text[:400], "language": user.language})
            return r.is_success
    except httpx.HTTPError:
        log.exception("channel %s failed", channel)
    return False


def notify_user(db: Session, user_id: int, text: str, elder_id: int | None = None, channel: str | None = None) -> Notification | None:
    user = db.get(User, user_id)
    if not user:
        return None
    urgent = text.lstrip("[").upper().startswith(URGENT)
    pref = channel or kv.settings_of(db, user.id).get("notify_channel") or (
        "ivr" if user.channel == "ivr" else "whatsapp" if user.channel == "whatsapp" else "sms" if user.channel == "sms" else "log")
    if _quiet(db, user, urgent):
        pref = "log"  # held in the portal inbox only during the person's quiet hours
    n = Notification(user_id=user_id, elder_id=elder_id, text=text, channel=pref)
    db.add(n)
    ok = _send(pref, user, text) if pref != "log" else False
    n.status = "sent" if ok else ("queued" if pref == "log" else "failed")
    if urgent and not ok and pref != "sms":  # urgent messages try SMS as a fallback
        n.status = "sent" if _send("sms", user, text) else n.status
    db.commit()
    log.warning("NOTIFY %s (%s) via %s: %s", user.name or user.id, user.phone, pref, text)
    return n
