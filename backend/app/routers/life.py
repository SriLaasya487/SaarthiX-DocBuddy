"""Companionship, wellbeing, cognitive, games, stories, messages, daily-life helpers, safety extras, community."""
import json
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import (ActivityLog, Alert, CareMember, CognitiveResult, CommunityPost, CommunityRoom, GameScore, LifeStory, Message,
                      Reminder, ScamReport, User, now)
from ..security import current_user, rate_limit, require_elder, require_role
from ..services import alerts as A
from ..services import assistant, insights, kv, places
from ..services import consent as C
from ..services import content as K
from ..services import rules

router = APIRouter(tags=["life"])


class TextReq(BaseModel):
    text: str


# ---------- companionship (DB-021), devotional (DB-047), news (DB-073) ----------
@router.post("/companion/chat")
def chat(body: TextReq, user: User = Depends(require_elder)):
    rate_limit(f"chat:{user.id}", 120)
    return assistant.chat(body.text)


@router.get("/companion/music")
def music(kind: str = "", user: User = Depends(require_elder), db: Session = Depends(get_db)):
    lang = {"hi": "hindi", "te": "telugu", "ta": "tamil", "bn": "bengali", "mr": "marathi", "kn": "kannada", "gu": "gujarati", "en": "english"}.get((user.language or "en")[:2], "")
    q = f"{kind or 'old classic songs'} {lang}"
    return {"query": q, "open": "https://www.youtube.com/results?search_query=" + quote(q), "note": "Opens a search; DocBuddy does not host music."}


@router.get("/devotional")
def devotional(faith: str = "", user: User = Depends(require_elder), db: Session = Depends(get_db)):
    st = kv.settings_of(db, user.id)
    f = (faith or st.get("faith") or "hindu").lower()
    items = [{"title": q.title(), "open": "https://www.youtube.com/results?search_query=" + quote(f"{q} {(user.language or 'en')[:2]}")} for q in K.DEVOTIONAL.get(f, K.DEVOTIONAL["hindu"])]
    out = {"faith": f, "items": items}
    if f == "muslim" and st.get("lat") is not None:
        out["prayer_times"] = rules.prayer_times(date.today(), st["lat"], st["lng"])
    return out


@router.get("/news")
def news(user: User = Depends(require_elder)):
    """Local-language headlines (RSS) + 'today in history' (Wikipedia). Both degrade quietly if offline."""
    lang = (user.language or "en")[:2]
    heads, hist = [], ""
    try:
        r = httpx.get(K.NEWS_FEEDS.get(lang, K.NEWS_FEEDS["en"]), timeout=8, follow_redirects=True)
        heads = [re.sub(r"<[^>]+>|<!\[CDATA\[|\]\]>", "", t).strip() for t in re.findall(r"<item>.*?<title>(.*?)</title>", r.text, re.S)][:6]
    except httpx.HTTPError:
        pass
    try:
        t = date.today()
        e = httpx.get(f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{t.month}/{t.day}", timeout=8).json()["events"]
        hist = f"On this day in {e[0]['year']}: {e[0]['text']}"
    except Exception:
        pass
    return {"headlines": heads, "today_in_history": hist, "speak": " ".join(heads[:5]) or "I could not reach the news right now."}


# ---------- calming (DB-046, DB-023) ----------
@router.get("/calm/breathing")
def breathing(user: User = Depends(require_elder)):
    return K.BREATHING


@router.get("/calm/steps")
def calm_steps(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return {"steps": K.ANXIETY_STEPS, "contacts_offer": True, "helpline": {"name": "Tele-MANAS", "number": "14416"},
            "note": "These are simple calming steps, not treatment."}


# ---------- games (DB-022, DB-050) ----------
@router.get("/games")
def games(user: User = Depends(require_elder)):
    return {k: v["name"] for k, v in K.GAMES.items()}


@router.get("/games/{game}/round")
def game_round(game: str, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    if game not in K.GAMES:
        raise HTTPException(404, "Unknown game")
    return insights.game_round(db, user.id, game)


class ScoreIn(BaseModel):
    level: int
    pct: int


@router.post("/games/{game}/score")
def game_score(game: str, body: ScoreIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    if game not in K.GAMES:
        raise HTTPException(404, "Unknown game")
    db.add(GameScore(elder_id=user.id, game=game, level=body.level, pct=max(0, min(100, body.pct)))); db.commit()
    return {"next_level": insights.next_level(db, user.id, game)}


# ---------- cognitive screening (DB-049) ----------
@router.get("/cognitive/start")
def cog_start(user: User = Depends(require_elder)):
    return insights.cognitive_start()


class CogIn(BaseModel):
    day: str = ""
    month: str = ""
    year: str = ""
    words: list[str] = []
    recall: str = ""
    digits: list[int] = []
    backwards: str = ""


@router.post("/cognitive/submit")
def cog_submit(body: CogIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    r = insights.cognitive_score(body.model_dump())
    changed = insights.cognitive_change(db, user.id, r["score"])
    db.add(CognitiveResult(elder_id=user.id, score=r["score"], max_score=r["max"])); db.commit()
    alert = A.ask_elder(db, user.id, "cognitive", "A memory exercise went differently from usual. This is not a diagnosis; a doctor visit may help.").id if changed else None
    return {**r, "changed": changed, "ask_to_inform_alert_id": alert,
            "speak": "Thank you. Your score is %d out of %d." % (r["score"], r["max"]) + (" It was a bit different from usual. Would you like me to tell your doctor or family so they can check in with you?" if changed else ""),
            "disclaimer": "This is a brain exercise, not a test for any illness. Only a doctor can assess memory."}


# ---------- life stories (DB-048) ----------
def _save(b64: str, ext: str) -> str:
    import base64
    d = Path(settings.media_dir); d.mkdir(parents=True, exist_ok=True)
    n = f"{uuid.uuid4().hex}.{re.sub(r'[^a-z0-9]', '', ext.lower())[:5] or 'webm'}"
    (d / n).write_bytes(base64.b64decode(b64)); return n


class StoryIn(BaseModel):
    title: str
    transcript: str = ""
    audio_b64: str = ""
    ext: str = "webm"


@router.post("/life-stories")
def story_add(body: StoryIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    s = LifeStory(elder_id=user.id, title=body.title, transcript=body.transcript, file_ref=_save(body.audio_b64, body.ext) if body.audio_b64 else "")
    db.add(s); db.commit()
    return {"id": s.id}


@router.get("/life-stories")
def story_list(elder_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    eid = user.id if user.role == "elder" else elder_id
    if user.role != "elder":
        C.require_view(db, eid, user, "life_story")
    return [{"id": s.id, "title": s.title, "transcript": s.transcript, "has_audio": bool(s.file_ref), "at": s.at}
            for s in db.scalars(select(LifeStory).where(LifeStory.elder_id == eid).order_by(LifeStory.id.desc())).all()]


@router.get("/life-stories/{sid}/audio")
def story_audio(sid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(LifeStory, sid)
    if not s or not s.file_ref:
        raise HTTPException(404, "Not found")
    if s.elder_id != user.id:
        C.require_view(db, s.elder_id, user, "life_story")
    return Response((Path(settings.media_dir) / s.file_ref).read_bytes(), media_type="audio/webm")


# ---------- grandchild connection (DB-052) ----------
class MsgIn(BaseModel):
    elder_id: int
    kind: str = "voice"  # voice | drawing | text
    text: str = ""
    file_b64: str = ""
    ext: str = "webm"


@router.post("/messages")
def send_message(body: MsgIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    C.require_scope(db, body.elder_id, user, "messages", "send")
    if body.kind not in {"voice", "drawing", "text"}:
        raise HTTPException(400, "Bad kind")
    if any(w in body.text.lower() for w in K.BANNED[:4]):
        raise HTTPException(400, "Please keep messages kind and simple")
    m = Message(elder_id=body.elder_id, sender_id=user.id, kind=body.kind, body=body.text, file_ref=_save(body.file_b64, body.ext) if body.file_b64 else "")
    db.add(m); db.commit()
    return {"id": m.id}


@router.get("/messages")
def my_messages(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(Message).where(Message.elder_id == user.id, Message.kind != "imfine").order_by(Message.id.desc()).limit(30)).all()
    return [{"id": m.id, "from": db.get(User, m.sender_id).name, "kind": m.kind, "text": m.body, "has_file": bool(m.file_ref), "played": m.played, "at": m.at,
             "speak": f"{db.get(User, m.sender_id).name} sent you a {m.kind} message. {m.body}"} for m in rows]


@router.get("/messages/{mid}/file")
def message_file(mid: int, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    m = db.get(Message, mid)
    if not m or m.elder_id != user.id or not m.file_ref:
        raise HTTPException(404, "Not found")
    m.played = True; db.commit()
    return Response((Path(settings.media_dir) / m.file_ref).read_bytes())


# ---------- nudges (DB-030) and activity (DB-031) ----------
@router.get("/nudges/due")
def nudges(hour: int | None = None, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return insights.nudges_due(db, user.id, hour if hour is not None else datetime.now().hour)


class ActIn(BaseModel):
    kind: str
    value: float = 1
    source: str = "manual"


@router.post("/activity")
def add_activity(body: ActIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    if body.kind not in {"sleep", "steps", "walk", "water", "meal"}:
        raise HTTPException(400, "Unknown kind")
    if body.source != "manual" and not kv.settings_of(db, user.id)["activity_tracking"]:
        raise HTTPException(403, "Passive sleep/activity tracking is off. You can turn it on in Settings.")  # opt-in only
    db.add(ActivityLog(elder_id=user.id, kind=body.kind, value=body.value, source=body.source)); db.commit()
    return {"ok": True}


@router.get("/activity/summary")
def activity(days: int = 7, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return insights.activity_summary(db, user.id, days)


# ---------- insights for the elder ----------
@router.get("/insights/mood")
def mood(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return insights.mood_trend(db, user.id)


@router.get("/insights/patterns")
def patterns(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return {"patterns": insights.patterns(db, user.id), "note": "Information only."}


# ---------- daily life: voice assistant (DB-067), helplines (DB-068), schemes (DB-069), lessons (DB-072) ----------
@router.post("/assistant/intent")
def assistant_intent(body: TextReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    contacts = []
    for m in db.scalars(select(CareMember).where(CareMember.elder_id == user.id, CareMember.active)).all():
        u = db.get(User, m.member_id); contacts.append({"name": u.name or u.phone, "relation": m.relation, "phone": u.phone})
    r = assistant.intent(body.text, contacts)
    if r["intent"] == "alarm" and r["action"]:
        r["action"]["reminder_endpoint"] = "POST /reminders"
    if r["intent"] == "chat":
        r["speak"] = assistant.chat(body.text)["reply"]
    return r


@router.get("/helplines")
def helplines(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    return K.HELPLINES + (kv.get(db, user.id, "helplines", []) or [])


class HelplineIn(BaseModel):
    name: str
    number: str


@router.post("/helplines")
def helpline_add(body: HelplineIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    cur = kv.get(db, user.id, "helplines", []) or []
    kv.put(db, user.id, "helplines", cur + [{"name": body.name, "number": body.number, "kind": "custom", "custom": True}])
    return {"ok": True}


@router.delete("/helplines/{number}")
def helpline_del(number: str, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    kv.put(db, user.id, "helplines", [h for h in (kv.get(db, user.id, "helplines", []) or []) if h["number"] != number])
    return {"ok": True}


@router.get("/schemes")
def schemes(age: int, income: str = "", pensioner: bool = False, user: User = Depends(require_elder)):
    """Indicative matches (income: low | bpl | ''). The catalogue is editable and carries verify=true where rules change."""
    out = []
    for s in K.SCHEMES:
        if age < s.get("min_age", 0):
            continue
        if s.get("income") == "bpl" and income != "bpl":
            continue
        if s.get("income") == "low" and income not in {"low", "bpl"}:
            continue
        if s.get("pensioner") and not pensioner:
            continue
        out.append(s)
    return {"matches": out, "disclaimer": "Indicative only. Rules and amounts change; confirm at the official site or your local office."}


@router.get("/lessons")
def lessons(user: User = Depends(require_elder)):
    return [{"id": l["id"], "title": l["title"]} for l in K.LESSONS]


@router.get("/lessons/{lid}")
def lesson(lid: str, user: User = Depends(require_elder)):
    l = next((x for x in K.LESSONS if x["id"] == lid), None)
    if not l:
        raise HTTPException(404, "Not found")
    return l


# ---------- safety extras ----------
class ScamIn(BaseModel):
    text: str
    source: str = ""


@router.post("/scam/check")
def scam_check(body: ScamIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    r = rules.scam_check(body.text)
    db.add(ScamReport(elder_id=user.id, source=body.source, text=body.text, risk=r["risk"])); db.commit()
    if r["level"] == "high":  # ask first - never tell family without the elder's yes
        r["ask_to_inform_alert_id"] = A.ask_elder(db, user.id, "scam", f"Received a suspicious {body.source or 'message/call'} that looks like a scam.").id
    return r


@router.get("/scam/tips")
def scam_tips(user: User = Depends(require_elder)):
    return {"tip": ["Never share your OTP with anyone - not even the bank.", "No police or CBI officer arrests anyone over video call.",
                    "You cannot win a lottery you never entered.", "Do not install apps a caller asks you to."][date.today().toordinal() % 4], "report": "1930"}


@router.get("/home-safety")
def home_safety(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    state = kv.get(db, user.id, "home_safety", {}) or {}
    items = [{"id": i, "text": t, "ok": state.get(i)} for i, t in K.HOME_SAFETY]
    return {"items": items, "score": sum(1 for x in items if x["ok"]), "total": len(items), "to_fix": [x["text"] for x in items if x["ok"] is False]}


class CheckItem(BaseModel):
    id: str
    ok: bool


@router.post("/home-safety")
def home_safety_set(body: CheckItem, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    state = kv.get(db, user.id, "home_safety", {}) or {}
    state[body.id] = body.ok; kv.put(db, user.id, "home_safety", state)
    return home_safety(user, db)


@router.get("/finder/{kind}")
def finder(kind: str, lat: float, lng: float, late: bool = False, user: User = Depends(require_elder)):
    if kind not in {"hospital", "pharmacy"}:
        raise HTTPException(404, "hospital or pharmacy")
    return places.find(kind, lat, lng, only_late=late) | {"emergency": {"ambulance": "tel:108", "emergency": "tel:112"}}


@router.get("/weather/advice")
def weather_advice(lat: float | None = None, lng: float | None = None, temp_c: float | None = None, aqi: float | None = None,
                   user: User = Depends(require_elder), db: Session = Depends(get_db)):
    st = kv.settings_of(db, user.id)
    lat, lng = lat if lat is not None else st.get("lat"), lng if lng is not None else st.get("lng")
    w = {"temp_c": temp_c, "aqi": aqi}
    if temp_c is None and aqi is None and lat is not None:
        w = places.weather(lat, lng)
    t = w.get("max_c") if w.get("max_c") is not None else w.get("temp_c")
    advice = rules.weather_advice(t, w.get("aqi"))
    suggest_disaster = bool((t is not None and t >= 44) or (w.get("aqi") or 0) >= 300)
    return {**w, "advice": advice, "speak": " ".join(advice), "suggest_disaster_mode": suggest_disaster}


class DisasterIn(BaseModel):
    on: bool
    kind: str = "heatwave"  # flood | heatwave | cyclone | cold | pollution


GUIDE = {"flood": ["Move to higher ground. Keep your medicines, torch and phone together.", "Do not walk or drive through flood water."],
         "heatwave": ["Stay in the coolest room. Drink water or ORS often.", "Check on neighbours."],
         "cyclone": ["Stay inside, away from windows.", "Keep medicines, torch, power bank and water ready."],
         "cold": ["Stay warm indoors. Wear layers.", "Do not use a coal heater in a closed room."],
         "pollution": ["Stay indoors, windows closed. Wear an N95 mask outside."]}


@router.post("/disaster")
def disaster_set(body: DisasterIn, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    kv.put(db, user.id, "disaster", {"on": body.on, "kind": body.kind, "since": str(now())})
    return disaster_get(user, db)


@router.get("/disaster")
def disaster_get(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    d = kv.get(db, user.id, "disaster", {"on": False}) or {"on": False}
    if not d.get("on"):
        return {"on": False, "checkin_times": ["09:00"]}
    return {**d, "checkin_times": ["08:00", "14:00", "20:00"], "guidance": GUIDE.get(d["kind"], []),
            "helplines": [h for h in K.HELPLINES if h["kind"] in {"emergency", "disaster"}], "speak": "Extra safety mode is on. " + " ".join(GUIDE.get(d["kind"], []))}


# ---------- community (DB-051) ----------
def _seed(db):
    if not db.scalars(select(CommunityRoom)).first():
        for n, a, i in K.COMMUNITY_SEED:
            db.add(CommunityRoom(name=n, area=a, interest=i))
        db.commit()


@router.get("/community/rooms")
def rooms(area: str = "", user: User = Depends(current_user), db: Session = Depends(get_db)):
    _seed(db)
    return [{"id": r.id, "name": r.name, "area": r.area, "interest": r.interest} for r in db.scalars(select(CommunityRoom)).all() if not area or r.area in {"", area}]


class RoomIn(BaseModel):
    name: str
    area: str = ""
    interest: str = ""


@router.post("/community/rooms")
def room_add(body: RoomIn, user: User = Depends(require_role("moderator")), db: Session = Depends(get_db)):
    r = CommunityRoom(**body.model_dump()); db.add(r); db.commit()
    return {"id": r.id}


@router.post("/community/join")
def community_join(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    s = kv.get(db, user.id, "settings", {}) or {}; s["community"] = True; kv.put(db, user.id, "settings", s)
    return {"joined": True}


@router.post("/community/rooms/{rid}/posts")
def post(rid: int, body: TextReq, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    if not kv.settings_of(db, user.id)["community"]:
        raise HTTPException(403, "Join the community first")
    low = body.text.lower()
    hidden = any(w in low for w in K.BANNED) or bool(re.search(r"\b\d{10}\b", low))  # no links, money talk or phone numbers
    p = CommunityPost(room_id=rid, user_id=user.id, text=body.text, hidden=hidden); db.add(p); db.commit()
    return {"id": p.id, "posted": not hidden, "note": "This message was held for a moderator." if hidden else ""}


@router.get("/community/rooms/{rid}/posts")
def posts(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(CommunityPost).where(CommunityPost.room_id == rid, CommunityPost.hidden.is_(False)).order_by(CommunityPost.id.desc()).limit(40)).all()
    return [{"id": p.id, "name": (db.get(User, p.user_id).name or "Friend").split()[0], "text": p.text, "at": p.at, "speak": p.text} for p in rows]


@router.post("/community/posts/{pid}/report")
def post_report(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(CommunityPost, pid)
    if not p:
        raise HTTPException(404, "Not found")
    p.reports += 1
    p.hidden = p.hidden or p.reports >= 2; db.commit()
    return {"ok": True}


@router.get("/community/moderation")
def mod_queue(user: User = Depends(require_role("moderator")), db: Session = Depends(get_db)):
    return [{"id": p.id, "text": p.text, "reports": p.reports} for p in db.scalars(select(CommunityPost).where(CommunityPost.hidden.is_(True))).all()]


@router.post("/community/moderation/{pid}")
def mod_decide(pid: int, approve: bool, user: User = Depends(require_role("moderator")), db: Session = Depends(get_db)):
    p = db.get(CommunityPost, pid)
    if not p:
        raise HTTPException(404, "Not found")
    if approve: p.hidden, p.reports = False, 0
    else: db.delete(p)
    db.commit()
    return {"ok": True}
