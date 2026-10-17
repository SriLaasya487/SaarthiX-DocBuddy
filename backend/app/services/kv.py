import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Kv

DEFAULT_SETTINGS = {
    "high_contrast": False, "font_scale": 1.0, "captions": True, "vibrate_flash": False, "speech_rate": 0.9,
    "dialect": "", "lite_mode": "auto", "nudges": {"hydration": {"on": True, "every_h": 3}, "meal": {"on": True},
                                                  "walk": {"on": False}},
    "activity_tracking": False, "faith": "", "city": "", "lat": None, "lng": None, "region": "",
    "pharmacy_phone": "", "auto_answer_video": [], "aggregate_opt_in": False, "community": False,
    "family_doctor_phone": "", "notify_channel": "", "quiet_hours": [22, 6],
}


def get(db: Session, elder_id: int, key: str, default=None):
    row = db.scalars(select(Kv).where(Kv.elder_id == elder_id, Kv.key == key)).first()
    if not row:
        return default
    try:
        return json.loads(row.value)
    except ValueError:
        return default


def put(db: Session, elder_id: int, key: str, value) -> None:
    row = db.scalars(select(Kv).where(Kv.elder_id == elder_id, Kv.key == key)).first()
    if row:
        row.value = json.dumps(value)
    else:
        db.add(Kv(elder_id=elder_id, key=key, value=json.dumps(value)))
    db.commit()


def settings_of(db: Session, elder_id: int) -> dict:
    return {**DEFAULT_SETTINGS, **(get(db, elder_id, "settings", {}) or {})}
