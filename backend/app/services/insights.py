"""Mood trends, gentle patterns, cognitive screening, adaptive games, good-news digest, aggregate insights."""
import json
import random
import re
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (ActivityLog, CheckIn, CognitiveResult, DoseLog, GameScore, Kv, Medicine, User, Vital, now)
from . import content as K
from . import kv
from .rules import tone

SCORE = {"good": 2, "okay": 1, "low": 0}


def mood_trend(db: Session, elder_id: int, days: int = 28) -> dict:
    since = now() - timedelta(days=days)
    rows = db.scalars(select(CheckIn).where(CheckIn.elder_id == elder_id, CheckIn.at >= since).order_by(CheckIn.at)).all()
    weeks: dict[int, list[float]] = {}
    for c in rows:
        w = (now() - c.at).days // 7
        weeks.setdefault(w, []).append(SCORE.get(c.mood, 1) + 0.3 * max(-2, min(2, tone(c.note))))
    series = [{"weeks_ago": w, "avg": round(sum(v) / len(v), 2), "n": len(v)} for w, v in sorted(weeks.items(), reverse=True)]
    low_weeks = [s for s in series if s["avg"] < 0.8 and s["n"] >= 3]
    persistent = len(low_weeks) >= 2 and {s["weeks_ago"] for s in low_weeks} >= {0, 1}
    return {"series": series, "persistent_low": persistent,
            "note": "Your mood has been low for a couple of weeks. Talking to someone can help. Shall I tell someone you trust?" if persistent else ""}


def patterns(db: Session, elder_id: int) -> list[str]:
    """Gentle, informational: e.g. tiredness several days in a row. Never a diagnosis."""
    rows = db.scalars(select(CheckIn).where(CheckIn.elder_id == elder_id).order_by(CheckIn.id.desc()).limit(5)).all()
    out = []
    if len(rows) >= 3 and all(r.mood == "low" for r in rows[:3]):
        out.append("You have felt low for 3 check-ins in a row.")
    if len(rows) >= 3 and all(r.pain != "none" for r in rows[:3]):
        out.append("You have mentioned pain on 3 check-ins in a row. You may want to meet a doctor.")
    if len(rows) >= 3 and sum("tired" in (r.note or "").lower() or "thaka" in (r.note or "").lower() for r in rows[:4]) >= 3:
        out.append("You have said you feel tired several times lately.")
    if len(rows) >= 3 and all(not r.took_medicines for r in rows[:3]):
        out.append("You said you did not take your medicines for 3 days. Please tell your doctor or family.")
    return out


# ---------- cognitive screening (orientation + recall + digits). Flags CHANGE, never diagnoses ----------
def cognitive_start() -> dict:
    words = random.sample(K.WORDS, 3)
    digits = [random.randint(1, 9) for _ in range(5)]
    return {"words": words, "digits": digits,
            "steps": ["Say today's day of the week.", "Say the month and the year.", "Remember these three words: " + ", ".join(words) + ".",
                      "Repeat these numbers backwards: " + " ".join(map(str, digits)) + ".", "Now say the three words again."]}


def cognitive_score(payload: dict, today: date | None = None) -> dict:
    today = today or date.today()
    pts, mx = 0, 8
    day = (payload.get("day") or "").lower()
    pts += 1 if today.strftime("%A").lower() in day else 0
    pts += 1 if today.strftime("%B").lower() in (payload.get("month") or "").lower() else 0
    pts += 1 if str(today.year) in str(payload.get("year") or "") else 0
    said = {w.strip().lower() for w in re.split(r"[ ,]+", payload.get("recall") or "") if w}
    pts += sum(w in said for w in payload.get("words", []))
    back = [int(x) for x in re.findall(r"\d", str(payload.get("backwards") or ""))]
    pts += 2 if back == list(reversed(payload.get("digits", []))) and back else (1 if back and set(back) == set(payload.get("digits", [])) else 0)
    return {"score": pts, "max": mx}


def cognitive_change(db: Session, elder_id: int, score: int) -> bool:
    prev = db.scalars(select(CognitiveResult).where(CognitiveResult.elder_id == elder_id).order_by(CognitiveResult.id.desc()).limit(4)).all()[1:]
    if len(prev) < 2:
        return False
    return score <= (sum(p.score for p in prev) / len(prev)) - 2


# ---------- adaptive games ----------
def next_level(db: Session, elder_id: int, game: str) -> int:
    rows = db.scalars(select(GameScore).where(GameScore.elder_id == elder_id, GameScore.game == game).order_by(GameScore.id.desc()).limit(3)).all()
    top = len(K.GAMES[game]["levels"]) - 1
    if not rows:
        return 0
    lvl = rows[0].level
    if len(rows) == 3 and all(r.pct >= 80 for r in rows) and all(r.level == lvl for r in rows):
        return min(top, lvl + 1)
    if rows[0].pct <= 40:
        return max(0, lvl - 1)
    return lvl


def game_round(db: Session, elder_id: int, game: str) -> dict:
    lvl = next_level(db, elder_id, game)
    size = K.GAMES[game]["levels"][lvl]
    spec = {"game": game, "level": lvl, "size": size}
    if game == "pairs":
        spec["symbols"] = random.sample(["🌸", "🐘", "🥭", "🪔", "🚲", "🌙", "🐦", "🍵", "⭐", "🐄", "🛕", "🪁"], size)
    elif game == "sequence":
        spec["sequence"] = [random.randint(0, 3) for _ in range(size)]
    else:
        spec["words"] = random.sample(K.WORDS, size)
    return spec


# ---------- good news ----------
def good_news(db: Session, elder_id: int, days: int = 7) -> list[str]:
    since = now() - timedelta(days=days)
    out = []
    meds = db.scalars(select(Medicine).where(Medicine.elder_id == elder_id, Medicine.active)).all()
    exp = sum(len(m.times.split(",")) for m in meds) * days
    taken = db.scalar(select(func.count(DoseLog.id)).where(DoseLog.elder_id == elder_id, DoseLog.taken_at >= since)) or 0
    if exp and taken >= exp:
        out.append("Took every medicine this week.")
    elif exp and taken / exp >= 0.85:
        out.append(f"Took {round(100 * taken / exp)}% of medicines this week - very good.")
    cis = db.scalars(select(CheckIn).where(CheckIn.elder_id == elder_id, CheckIn.at >= since)).all()
    g = sum(c.mood == "good" for c in cis)
    if g:
        out.append(f"Felt good on {g} day(s).")
    if len({c.at.date() for c in cis}) >= 5:
        out.append(f"Checked in on {len({c.at.date() for c in cis})} days.")
    walks = db.scalar(select(func.count(ActivityLog.id)).where(ActivityLog.elder_id == elder_id, ActivityLog.kind == "walk", ActivityLog.at >= since)) or 0
    if walks:
        out.append(f"Went for {walks} walk(s).")
    vs = db.scalars(select(Vital).where(Vital.elder_id == elder_id, Vital.at >= since)).all()
    if len(vs) >= 3 and not any(v.flagged for v in vs):
        out.append("All readings were in the usual range.")
    return out


# ---------- sleep & activity summary ----------
def activity_summary(db: Session, elder_id: int, days: int = 7) -> dict:
    since = now() - timedelta(days=days)
    rows = db.scalars(select(ActivityLog).where(ActivityLog.elder_id == elder_id, ActivityLog.at >= since)).all()
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r.kind, []).append(r.value)
    avg = lambda k: round(sum(by[k]) / len(by[k]), 1) if k in by else None
    return {"days": days, "avg_sleep_hours": avg("sleep"), "avg_steps": avg("steps"), "walks": len(by.get("walk", [])),
            "water_glasses_per_day": round(sum(by.get("water", [])) / days, 1) if "water" in by else None}


# ---------- nudges ----------
def nudges_due(db: Session, elder_id: int, hour: int) -> list[dict]:
    cfg = kv.settings_of(db, elder_id)["nudges"]
    today = datetime.combine(date.today(), datetime.min.time())
    done = {r.kind for r in db.scalars(select(ActivityLog).where(ActivityLog.elder_id == elder_id, ActivityLog.at >= today)).all()}
    out = []
    if cfg.get("hydration", {}).get("on") and 8 <= hour <= 20 and hour % max(1, int(cfg["hydration"].get("every_h", 3))) == 0:
        out.append({"kind": "water", "say": "Time for a glass of water."})
    if cfg.get("meal", {}).get("on") and hour in (8, 13, 20) and "meal" not in done:
        out.append({"kind": "meal", "say": {8: "Have you had breakfast?", 13: "It is lunch time.", 20: "Please have your dinner."}[hour]})
    if cfg.get("walk", {}).get("on") and hour in (7, 17) and "walk" not in done:
        out.append({"kind": "walk", "say": "A short gentle walk would feel nice."})
    return out


# ---------- aggregate (de-identified, k-anonymous) ----------
K_MIN = 5


def aggregate(db: Session) -> dict:
    elders = [u for u in db.scalars(select(User).where(User.role == "elder")).all() if kv.settings_of(db, u.id).get("aggregate_opt_in")]
    cells: dict[str, list[dict]] = {}
    for u in elders:
        region = kv.settings_of(db, u.id).get("region") or "unknown"
        cis = db.scalars(select(CheckIn).where(CheckIn.elder_id == u.id, CheckIn.at >= now() - timedelta(days=30))).all()
        vs = db.scalars(select(Vital).where(Vital.elder_id == u.id, Vital.at >= now() - timedelta(days=30))).all()
        cells.setdefault(region, []).append({"good": sum(c.mood == "good" for c in cis), "low": sum(c.mood == "low" for c in cis), "n": len(cis),
                                              "flag": sum(v.flagged for v in vs), "vn": len(vs)})
    out, suppressed = [], 0
    for region, rows in cells.items():
        if len(rows) < K_MIN:
            suppressed += 1
            continue
        n, vn = sum(r["n"] for r in rows), sum(r["vn"] for r in rows)
        out.append({"region": region, "elders": (len(rows) // K_MIN) * K_MIN, "low_mood_pct": round(100 * sum(r["low"] for r in rows) / n) if n else None,
                    "flagged_reading_pct": round(100 * sum(r["flag"] for r in rows) / vn) if vn else None})
    return {"k_anonymity_min": K_MIN, "regions": out, "suppressed_regions": suppressed,
            "note": "Only elders who opted in are counted. Regions with fewer than %d people are hidden. Counts are rounded down." % K_MIN}
