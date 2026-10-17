"""Tiered pricing (DB-090). Safety is NEVER gated: SOS, fall detection, consent, emergency card, medicine reminders and daily check-in are free forever."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Subscription, now

TIERS = ["free", "family", "care"]
ALWAYS_FREE = ["Voice-first app in 8 languages", "Medicine reminders", "Daily check-in", "SOS and fall detection", "Emergency card",
               "Consent controls and audit log", "1 family member view"]
FEATURE_TIER = {"whatsapp_alerts": "family", "family_portal_multi": "family", "reports_shared": "family", "digest": "family",
                "care_team_roles": "care", "ivr": "care", "teleconsult": "care", "devices": "care", "records_locker_unlimited": "care",
                "cost_sharing": "family", "video": "family", "nri_services": "care", "locker": "free"}


def pricing() -> dict:
    return {"currency": "INR", "tiers": [
        {"id": "free", "price_per_month": 0, "includes": ALWAYS_FREE},
        {"id": "family", "price_per_month": settings.price_family_inr, "includes": ["Everything in Free", "Unlimited family members", "WhatsApp/SMS alerts", "Shared weekly reports and good-news digest", "Video calls", "Cost sharing"]},
        {"id": "care", "price_per_month": settings.price_care_inr, "includes": ["Everything in Family", "Care team roles and task board", "Phone-call (IVR) check-ins", "Teleconsult booking", "Bluetooth devices", "Unlimited records locker", "NRI local-help services"]}],
        "note": "Prices are placeholders set by the operator (PRICE_FAMILY_INR / PRICE_CARE_INR)."}


def tier_of(db: Session, elder_id: int) -> str:
    s = db.get(Subscription, elder_id)
    return s.tier if s and (not s.valid_until or s.valid_until > now()) else "free"


def allowed(db: Session, elder_id: int, feature: str) -> bool:
    if not settings.enforce_tiers:
        return True
    return TIERS.index(tier_of(db, elder_id)) >= TIERS.index(FEATURE_TIER.get(feature, "free"))


def gate(db: Session, elder_id: int, feature: str):
    if not allowed(db, elder_id, feature):
        raise HTTPException(402, f"This needs the {FEATURE_TIER[feature]} plan")
