"""Family side: care team + roles, task board, costs, video, nudges, burnout, NRI help, digest, 'I am fine', nominee."""
import json
import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (CallLog, CareMember, CareTask, CheckIn, Consent, ConsentProposal, Expense, Handover, Message, NomineeEvent,
                      NomineeRequest, Notification, ServiceRequest, Subscription, User, VideoCall, WellbeingCheck, now)
from ..security import current_user, require_elder
from ..services import consent as C
from ..services import insights, kv
from ..services.notify import local_time, notify_user
from ..services.pricing import gate

router = APIRouter(tags=["care"])


def _need_team(db, elder_id, user):
    if not C.is_team(db, elder_id, user.id):
        raise HTTPException(403, "You are not part of this person's care team")


# ---------- multiple caregivers with roles (DB-053, DB-062, DB-080) ----------
class InviteReq(BaseModel):
    elder_phone: str = ""        # when a family member proposes remotely (or give elder_id if already connected)
    elder_id: int | None = None
    member_phone: str
    member_name: str = ""
    role: str                    # primary|sibling|doctor|neighbour|chw|grandchild|guardian|nominee
    relation: str = ""
    days: int | None = None


@router.post("/care-team/invite")
def invite(body: InviteReq, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Elder invites -> proposal waits for the elder's own yes (by voice or button). A family member can propose remotely
    (caregiver-assisted setup); it is inert until the elder approves every item."""
    if body.role not in C.ROLE_BUNDLES:
        raise HTTPException(400, "Unknown role")
    if user.role == "elder":
        elder = user
    else:
        elder = db.get(User, body.elder_id) if body.elder_id else db.scalars(select(User).where(User.phone == body.elder_phone, User.role == "elder")).first()
        if elder and body.elder_id and not (C.is_team(db, elder.id, user.id) or db.scalars(select(Consent).where(Consent.elder_id == elder.id, Consent.grantee_id == user.id)).first()):
            elder = None  # elder_id alone only works for people already connected to this elder
        if not elder or elder.role != "elder":
            raise HTTPException(404, "No elder with that number")
        if len(db.scalars(select(ConsentProposal).where(ConsentProposal.elder_id == elder.id, ConsentProposal.proposer_id == user.id,
                                                        ConsentProposal.status == "pending")).all()) >= 5:
            raise HTTPException(429, "Too many waiting proposals. Ask them to answer the earlier ones first.")
    m = db.scalars(select(User).where(User.phone == body.member_phone)).first()
    if not m:
        m = User(phone=body.member_phone, name=body.member_name, role="doctor" if body.role == "doctor" else "family"); db.add(m); db.commit()
    items = [{"data_type": t, "scope": s} for t, s in C.ROLE_BUNDLES[body.role]]
    p = ConsentProposal(elder_id=elder.id, proposer_id=user.id, grantee_id=m.id, role=body.role, relation=body.relation, items=json.dumps(items), days=body.days)
    db.add(p); db.commit()
    notify_user(db, elder.id, f"{user.name or user.phone} suggests adding {m.name or m.phone} as {body.role}. Open DocBuddy to say yes or no.", elder.id)
    return {"proposal_id": p.id, "status": "pending_elder_approval", "items": items}


@router.get("/care-team")
def team(elder_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    eid = user.id if user.role == "elder" else elder_id
    if eid is None:
        raise HTTPException(400, "elder_id required")
    _need_team(db, eid, user)
    rows = db.scalars(select(CareMember).where(CareMember.elder_id == eid, CareMember.active)).all()
    cur = db.scalars(select(Handover).where(Handover.elder_id == eid).order_by(Handover.week_start.desc())).first()
    return {"members": [{"id": m.member_id, "name": (db.get(User, m.member_id).name or db.get(User, m.member_id).phone), "role": m.role,
                         "relation": m.relation, "priority": m.priority} for m in rows],
            "responsible_this_week": cur.responsible_id if cur and cur.week_start >= date.today() - timedelta(days=date.today().weekday()) else None}


class HandoverReq(BaseModel):
    elder_id: int
    responsible_id: int


@router.post("/care-team/handover")
def handover(body: HandoverReq, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if C.team_role(db, body.elder_id, user.id) != "primary":
        raise HTTPException(403, "Only the primary caregiver can hand over")
    if not C.is_team(db, body.elder_id, body.responsible_id):
        raise HTTPException(400, "That person is not on the care team")
    ws = date.today() - timedelta(days=date.today().weekday())
    db.add(Handover(elder_id=body.elder_id, week_start=ws, responsible_id=body.responsible_id, set_by=user.id)); db.commit()
    notify_user(db, body.responsible_id, f"You are the responsible caregiver for {db.get(User, body.elder_id).name} this week.", body.elder_id)
    return {"ok": True}


class MemberPatch(BaseModel):
    priority: int


@router.patch("/care-team/{elder_id}/{member_id}")
def patch_member(elder_id: int, member_id: int, body: MemberPatch, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    m = db.scalars(select(CareMember).where(CareMember.elder_id == user.id, CareMember.member_id == member_id)).first()
    if not m or elder_id != user.id:
        raise HTTPException(404, "Not found")
    m.priority = body.priority; db.commit()
    return {"ok": True}


# ---------- care task board (DB-054) ----------
class TaskIn(BaseModel):
    elder_id: int
    title: str
    due_on: date | None = None


def _task(db, t: CareTask):
    c = db.get(User, t.claimed_by) if t.claimed_by else None
    return {"id": t.id, "title": t.title, "due_on": t.due_on, "claimed_by": c.name or c.phone if c else None, "claimed_by_id": t.claimed_by, "done": t.done}


@router.post("/tasks")
def add_task(body: TaskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _need_team(db, body.elder_id, user)
    t = CareTask(elder_id=body.elder_id, title=body.title, due_on=body.due_on, created_by=user.id)
    db.add(t); db.commit()
    for m in db.scalars(select(CareMember).where(CareMember.elder_id == body.elder_id, CareMember.active)).all():
        if m.member_id != user.id and m.role in {"primary", "sibling", "grandchild"}:
            notify_user(db, m.member_id, f"New care task: {t.title}. Claim it in DocBuddy.", body.elder_id)
    return _task(db, t)


@router.get("/tasks")
def tasks(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _need_team(db, elder_id, user)
    return [_task(db, t) for t in db.scalars(select(CareTask).where(CareTask.elder_id == elder_id).order_by(CareTask.done, CareTask.id.desc())).all()]


class TaskAct(BaseModel):
    action: str  # claim | release | done


@router.post("/tasks/{tid}")
def act_task(tid: int, body: TaskAct, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(CareTask, tid)
    if not t:
        raise HTTPException(404, "Not found")
    _need_team(db, t.elder_id, user)
    if body.action == "claim":
        if t.claimed_by and t.claimed_by != user.id:
            raise HTTPException(409, "Someone has already claimed this")
        t.claimed_by = user.id
    elif body.action == "release" and t.claimed_by == user.id:
        t.claimed_by = None
    elif body.action == "done":
        t.done = True
    db.commit()
    return _task(db, t)


# ---------- cost sharing (DB-055) ----------
class ExpenseIn(BaseModel):
    elder_id: int
    amount: float
    what: str
    split_with: list[int] = []


@router.post("/expenses")
def add_expense(body: ExpenseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _need_team(db, body.elder_id, user)
    e = Expense(elder_id=body.elder_id, paid_by=user.id, amount=body.amount, what=body.what, split_with=",".join(map(str, body.split_with)))
    db.add(e); db.commit()
    return {"id": e.id}


@router.get("/expenses")
def expenses(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Balances: positive = is owed money, negative = owes. Elder's own share is not counted (family bears it)."""
    _need_team(db, elder_id, user)
    family = [m.member_id for m in db.scalars(select(CareMember).where(CareMember.elder_id == elder_id, CareMember.active,
                                                                      CareMember.role.in_(["primary", "sibling"]))).all()]
    bal: dict[int, float] = {}
    rows = db.scalars(select(Expense).where(Expense.elder_id == elder_id, Expense.settled.is_(False))).all()
    for e in rows:
        part = [int(x) for x in e.split_with.split(",") if x] or family or [e.paid_by]
        part = sorted(set(part) | {e.paid_by})
        for p in part:
            bal[p] = bal.get(p, 0) - e.amount / len(part)
        bal[e.paid_by] = bal.get(e.paid_by, 0) + e.amount
    # who pays whom
    debtors = sorted([[u, -b] for u, b in bal.items() if b < -0.01], key=lambda x: -x[1])
    creditors = sorted([[u, b] for u, b in bal.items() if b > 0.01], key=lambda x: -x[1])
    pay = []
    for d in debtors:
        for c in creditors:
            x = min(d[1], c[1])
            if x > 0.01:
                pay.append({"from": d[0], "to": c[0], "amount": round(x, 2)}); d[1] -= x; c[1] -= x
    return {"total": round(sum(e.amount for e in rows), 2), "balances": {str(k): round(v, 2) for k, v in bal.items()}, "settle_up": pay,
            "items": [{"id": e.id, "what": e.what, "amount": e.amount, "paid_by": e.paid_by, "at": e.at} for e in rows]}


@router.post("/expenses/settle")
def settle(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _need_team(db, elder_id, user)
    for e in db.scalars(select(Expense).where(Expense.elder_id == elder_id, Expense.settled.is_(False))).all():
        e.settled = True
    db.commit()
    return {"ok": True}


# ---------- video call (DB-056) ----------
@router.post("/video/call/{elder_id}")
def start_call(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    C.require_scope(db, elder_id, user, "video", "send")
    auto = user.id in (kv.settings_of(db, elder_id).get("auto_answer_video") or [])
    v = VideoCall(elder_id=elder_id, caller_id=user.id, room_url=f"https://meet.jit.si/docbuddy-{secrets.token_urlsafe(10)}",
                  status="accepted" if auto else "ringing", auto_answered=auto)
    db.add(v); db.commit()
    notify_user(db, elder_id, f"{user.name or user.phone} is calling you on video.", elder_id)
    return {"id": v.id, "room_url": v.room_url, "auto_answered": auto}


@router.get("/video/incoming")
def incoming(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(VideoCall).where(VideoCall.elder_id == user.id, VideoCall.at >= now() - timedelta(minutes=2),
                                              VideoCall.status.in_(["ringing", "accepted"]), VideoCall.auto_answered.is_(True) | (VideoCall.status == "ringing"))).all()
    return [{"id": v.id, "from": db.get(User, v.caller_id).name, "room_url": v.room_url, "auto_answered": v.auto_answered, "status": v.status} for v in rows]


class CallAns(BaseModel):
    accept: bool


@router.post("/video/{vid}")
def answer(vid: int, body: CallAns, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    v = db.get(VideoCall, vid)
    if not v or v.elder_id != user.id:
        raise HTTPException(404, "Not found")
    v.status = "accepted" if body.accept else "declined"; db.commit()
    return {"status": v.status, "room_url": v.room_url if body.accept else ""}


# ---------- 'call your parents' nudge (DB-024) ----------
@router.post("/family/elders/{elder_id}/called")
def called(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(CallLog(user_id=user.id, elder_id=elder_id)); db.commit()
    return {"ok": True}


@router.get("/family/call-nudges")
def call_nudges(user: User = Depends(current_user), db: Session = Depends(get_db)):
    ids = {c.elder_id for c in db.scalars(select(Consent).where(Consent.grantee_id == user.id, Consent.revoked_at.is_(None))).all() if C._active(c)}
    ids |= {m.elder_id for m in db.scalars(select(CareMember).where(CareMember.member_id == user.id, CareMember.active)).all()}
    start = datetime.combine(local_time(user).date(), datetime.min.time())
    out = []
    for eid in ids:
        if not db.scalars(select(CallLog).where(CallLog.user_id == user.id, CallLog.elder_id == eid, CallLog.at >= now() - timedelta(hours=24))).first():
            e = db.get(User, eid)
            out.append({"elder_id": eid, "name": e.name, "say": f"You have not called {e.name} today. A short call means a lot.",
                        "elder_local_time": local_time(e).strftime("%I:%M %p")})
    return out


# ---------- caregiver burnout check (DB-058) ----------
BURNOUT_Q = ["I feel tired most days.", "I have little time for myself.", "I feel worried about doing enough.", "I sleep badly because of caring tasks.", "I do not get help from others."]


@router.get("/caregiver/wellbeing/questions")
def burnout_q(user: User = Depends(current_user)):
    return {"questions": BURNOUT_Q, "scale": "0 = never, 1 = sometimes, 2 = often"}


class BurnoutIn(BaseModel):
    answers: list[int]


@router.post("/caregiver/wellbeing")
def burnout(body: BurnoutIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if len(body.answers) != len(BURNOUT_Q) or any(a not in (0, 1, 2) for a in body.answers):
        raise HTTPException(400, "Answer all questions with 0, 1 or 2")
    s = sum(body.answers)
    level = "high" if s >= 7 else "medium" if s >= 4 else "low"
    db.add(WellbeingCheck(user_id=user.id, score=s, level=level)); db.commit()
    tips = {"low": ["You are coping well. Keep some time for yourself each day."],
            "medium": ["Share a task on the care board.", "Plan a short break this week.", "Talk to a friend about how you feel."],
            "high": ["Please ask your siblings to take over some tasks this week (use the care board).", "Speak to your own doctor or a counsellor.",
                     "Tele-MANAS 14416 offers free mental-health support.", "Consider paid respite help through NRI/local services."]}[level]
    return {"score": s, "level": level, "tips": tips, "note": "This is a check-in, not a diagnosis."}


# ---------- NRI mode (DB-059) ----------
class ServiceIn(BaseModel):
    elder_id: int
    kind: str  # nurse|driver|groceries|other
    when: datetime
    notes: str = ""
    amount: float = 0


@router.post("/services")
def request_service(body: ServiceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """The family member books and pays; the elder is asked first because someone will come to the house."""
    C.require_scope(db, body.elder_id, user, "services", "send")
    s = ServiceRequest(elder_id=body.elder_id, requester_id=user.id, **body.model_dump(exclude={"elder_id"}))
    s.payment_link = f"upi://pay?pn=DocBuddy%20Help&am={body.amount:g}&tn=Care%20{body.kind}" if body.amount else ""
    db.add(s); db.commit()
    e = db.get(User, body.elder_id)
    notify_user(db, body.elder_id, f"{user.name} would like a {body.kind} to visit on {local_time(e, body.when):%d %b at %I:%M %p}. Say yes or no in DocBuddy.", body.elder_id)
    return {"id": s.id, "status": s.status, "elder_local_time": f"{local_time(e, body.when):%d %b %I:%M %p}", "payment_link": s.payment_link}


@router.get("/services/pending")
def services_pending(user: User = Depends(require_elder), db: Session = Depends(get_db)):
    rows = db.scalars(select(ServiceRequest).where(ServiceRequest.elder_id == user.id, ServiceRequest.status == "pending_elder")).all()
    return [{"id": s.id, "kind": s.kind, "when": s.when, "from": db.get(User, s.requester_id).name,
             "speak": f"{db.get(User, s.requester_id).name} wants a {s.kind} to visit on {s.when:%d %b at %I:%M %p}. Is that okay?"} for s in rows]


@router.post("/services/{sid}")
def service_decide(sid: int, body: CallAns, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    s = db.get(ServiceRequest, sid)
    if not s or s.elder_id != user.id:
        raise HTTPException(404, "Not found")
    s.status = "approved" if body.accept else "declined"; db.commit()
    notify_user(db, s.requester_id, f"{user.name} {'approved' if body.accept else 'declined'} the {s.kind} visit.", user.id)
    return {"status": s.status}


@router.get("/inbox")
def inbox(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(50)).all()
    return [{"id": n.id, "text": n.text, "at": local_time(user, n.at).isoformat(), "channel": n.channel, "status": n.status} for n in rows]


# ---------- weekly good-news digest (DB-057) ----------
@router.get("/family/elders/{elder_id}/digest")
def digest(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    C.require_view(db, elder_id, user, "reports")
    e = db.get(User, elder_id)
    news = insights.good_news(db, elder_id)
    return {"elder": e.name, "good_news": news, "say": f"Good news about {e.name}: " + " ".join(news) if news else f"Nothing special this week for {e.name} - a quiet week."}


# ---------- daily 'I am fine' (DB-015) ----------
@router.post("/imfine")
def imfine(approve: bool = False, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """Without approve=true this only returns the draft. The message goes out only after the elder says yes."""
    draft = f"{user.name or 'Your parent'} says: I am fine today."
    if not approve:
        return {"draft": draft, "speak": "Shall I tell your family that you are fine?", "sent_to": 0}
    ids = [c.grantee_id for c in db.scalars(select(Consent).where(Consent.elder_id == user.id, Consent.data_type == "imfine", Consent.revoked_at.is_(None))).all() if C._active(c)]
    for i in set(ids):
        db.add(Message(elder_id=user.id, sender_id=user.id, kind="imfine", body=draft))
        notify_user(db, i, draft, user.id)
    db.commit()
    return {"sent_to": len(set(ids)), "speak": "Done. Your family knows you are fine."}


# ---------- nominee / incapacity (DB-084) ----------
class NomineeReq(BaseModel):
    elder_id: int
    reason: str


def _ev(db, rid, actor, what):
    db.add(NomineeEvent(request_id=rid, actor_id=actor, what=what)); db.commit()


@router.post("/nominee/request")
def nominee_request(body: NomineeReq, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if C.team_role(db, body.elder_id, user.id) != "nominee":
        raise HTTPException(403, "Only a nominee the elder named earlier can start this")
    r = NomineeRequest(elder_id=body.elder_id, nominee_id=user.id, reason=body.reason); db.add(r); db.commit()
    _ev(db, r.id, user.id, "Request filed: " + body.reason[:120])
    return {"id": r.id, "needs": "A doctor on the care team AND a guardian or primary caregiver must both approve"}


@router.post("/nominee/{rid}/approve")
def nominee_approve(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(NomineeRequest, rid)
    if not r or r.status != "pending":
        raise HTTPException(404, "Not found")
    role = C.team_role(db, r.elder_id, user.id)
    if role not in {"doctor", "guardian", "primary"} or user.id == r.nominee_id:
        raise HTTPException(403, "Only a doctor, guardian or primary caregiver (not the nominee) can approve")
    ap = json.loads(r.approvals)
    if any(a["user_id"] == user.id for a in ap):
        raise HTTPException(409, "Already approved by you")
    ap.append({"user_id": user.id, "role": role, "at": now().isoformat()}); r.approvals = json.dumps(ap); db.commit()
    _ev(db, rid, user.id, f"Approved as {role}")
    roles = {a["role"] for a in ap}
    if "doctor" in roles and roles & {"guardian", "primary"}:
        r.status, r.expires_at = "active", now() + timedelta(days=30)
        for t, s in C.NOMINEE_BUNDLE:
            C.grant(db, r.elder_id, r.nominee_id, t, s, 30)
        db.commit(); _ev(db, rid, user.id, "Access granted for 30 days (health decisions only)")
        notify_user(db, r.elder_id, "Your nominee has been given limited access to your health information. You can end it any time.", r.elder_id)
    return {"status": r.status, "approvals": ap}


@router.get("/nominee/{rid}/audit")
def nominee_audit(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(NomineeRequest, rid)
    if not r or not C.is_team(db, r.elder_id, user.id):
        raise HTTPException(404, "Not found")
    return [{"at": e.at, "actor": db.get(User, e.actor_id).name, "what": e.what} for e in db.scalars(select(NomineeEvent).where(NomineeEvent.request_id == rid)).all()]


@router.post("/nominee/{rid}/restore")
def nominee_restore(rid: int, user: User = Depends(require_elder), db: Session = Depends(get_db)):
    """The elder can end the nominee's access whenever they are able to speak for themselves."""
    r = db.get(NomineeRequest, rid)
    if not r or r.elder_id != user.id:
        raise HTTPException(404, "Not found")
    for c in db.scalars(select(Consent).where(Consent.elder_id == user.id, Consent.grantee_id == r.nominee_id, Consent.revoked_at.is_(None))).all():
        c.revoked_at = now()
    r.status = "restored"; db.commit(); _ev(db, rid, user.id, "Elder restored control and ended nominee access")
    return {"status": "restored"}
