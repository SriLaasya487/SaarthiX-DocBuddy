from datetime import datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .crypto import EncryptedText
from .db import Base


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    role: Mapped[str] = mapped_column(String(10), default="elder")  # elder|family|doctor|chw|partner|moderator
    language: Mapped[str] = mapped_column(String(10), default="hi-IN")
    timezone: Mapped[str] = mapped_column(String(40), default="Asia/Kolkata")
    channel: Mapped[str] = mapped_column(String(10), default="app")  # app | ivr (feature phone) | whatsapp | sms
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Consent(Base):
    """Elder -> grantee permission for one data type. Revocable, optionally expiring."""
    __tablename__ = "consents"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    grantee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    data_type: Mapped[str] = mapped_column(String(30))
    scope: Mapped[str] = mapped_column(String(10), default="view")  # view | escalate | send | write
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AccessLog(Base):
    __tablename__ = "access_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    data_type: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(30), default="view")
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Medicine(Base):
    __tablename__ = "medicines"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    tablets: Mapped[int] = mapped_column(Integer, default=1)
    times: Mapped[str] = mapped_column(String(80), default="08:00")  # comma separated HH:MM
    stock: Mapped[int] = mapped_column(Integer, default=0)
    missed_dose_note: Mapped[str] = mapped_column(Text, default="")  # doctor-approved wording only
    color: Mapped[str] = mapped_column(String(20), default="")       # for pill-box photo verification
    generic_name: Mapped[str] = mapped_column(String(80), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DoseLog(Base):
    __tablename__ = "dose_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"), index=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    slot: Mapped[str] = mapped_column(String(5))
    taken_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CheckIn(Base):
    __tablename__ = "checkins"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)
    mood: Mapped[str] = mapped_column(String(10))  # good | okay | low
    pain: Mapped[str] = mapped_column(String(10), default="none")  # none | mild | strong
    took_medicines: Mapped[bool] = mapped_column(Boolean, default=True)
    needs_help: Mapped[bool] = mapped_column(Boolean, default=False)
    doctor_visit_soon: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")


class Vital(Base):
    __tablename__ = "vitals"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # bp | sugar | spo2 | pulse
    value1: Mapped[float] = mapped_column(Float)
    value2: Mapped[float | None] = mapped_column(Float, nullable=True)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(12), default="voice")  # voice | manual | device | chw | wearable
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    doctor: Mapped[str] = mapped_column(String(80))
    at: Mapped[datetime] = mapped_column(DateTime)
    note: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(10), default="visit")  # visit | tele
    join_url: Mapped[str] = mapped_column(String(200), default="")
    reminded: Mapped[int] = mapped_column(Integer, default=0)       # 0 none, 1 day-before, 2 hour-before


class EmergencyCard(Base):
    __tablename__ = "emergency_cards"
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    blood_group: Mapped[str] = mapped_column(String(5), default="")
    allergies: Mapped[str] = mapped_column(Text, default="")
    doctor_phone: Mapped[str] = mapped_column(String(20), default="")
    doctor_name: Mapped[str] = mapped_column(String(80), default="")
    conditions: Mapped[str] = mapped_column(Text, default="")
    contacts: Mapped[str] = mapped_column(Text, default="")  # "Name:phone;Name:phone"


class Alert(Base):
    """Escalation. 'pending_elder' = asked elder first; sent only if elder allows (or SOS pressed)."""
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # sos | fall | help | low_mood | missed_dose | scam | cognitive
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(15), default="pending_elder")  # pending_elder|sent|declined|cancelled
    auto_escalate_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    location: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class OtpCode(Base):
    __tablename__ = "otp_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


# ======================= v2: the rest of the 90-feature catalog =======================
def _fk(index=True):
    return mapped_column(ForeignKey("users.id"), index=index)


class Kv(Base):
    """Small per-elder JSON documents: settings, checklists, vaccination dates, disaster mode ..."""
    __tablename__ = "kv"
    __table_args__ = (UniqueConstraint("elder_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    key: Mapped[str] = mapped_column(String(40))
    value: Mapped[str] = mapped_column(Text, default="{}")


class Notification(Base):
    """Outbox: every message DocBuddy sends to a person (also what the portal 'inbox' shows)."""
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _fk()
    elder_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(10), default="log")
    status: Mapped[str] = mapped_column(String(10), default="queued")  # queued | sent | failed
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class DoseSnooze(Base):
    __tablename__ = "dose_snooze"
    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"), index=True)
    elder_id: Mapped[int] = _fk()
    slot: Mapped[str] = mapped_column(String(5))
    day: Mapped[str] = mapped_column(String(10))
    until: Mapped[datetime] = mapped_column(DateTime)
    count: Mapped[int] = mapped_column(Integer, default=1)


class CareMember(Base):
    __tablename__ = "care_members"
    __table_args__ = (UniqueConstraint("elder_id", "member_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    member_id: Mapped[int] = _fk()
    role: Mapped[str] = mapped_column(String(12))  # primary|sibling|doctor|neighbour|chw|nominee|guardian|grandchild
    relation: Mapped[str] = mapped_column(String(20), default="")  # how the elder calls them: son, daughter...
    priority: Mapped[int] = mapped_column(Integer, default=5)     # 1 = reached first (e.g. neighbour)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ConsentProposal(Base):
    """A family member proposes; nothing happens until the elder approves (caregiver-assisted setup)."""
    __tablename__ = "consent_proposals"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    proposer_id: Mapped[int] = _fk()
    grantee_id: Mapped[int] = _fk()
    role: Mapped[str] = mapped_column(String(12), default="")
    relation: Mapped[str] = mapped_column(String(20), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")  # json [{data_type, scope}]
    days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending|approved|declined
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Handover(Base):
    __tablename__ = "handovers"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    week_start: Mapped[datetime] = mapped_column(Date)
    responsible_id: Mapped[int] = _fk(False)
    set_by: Mapped[int] = _fk(False)


class CareTask(Base):
    __tablename__ = "care_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    title: Mapped[str] = mapped_column(String(160))
    due_on: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    claimed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = _fk(False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    paid_by: Mapped[int] = _fk(False)
    amount: Mapped[float] = mapped_column(Float)
    what: Mapped[str] = mapped_column(String(120))
    split_with: Mapped[str] = mapped_column(Text, default="")  # comma separated user ids (incl. payer); empty = whole team
    settled: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class SymptomNote(Base):
    __tablename__ = "symptom_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    text: Mapped[str] = mapped_column(EncryptedText)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Document(Base):
    """Records locker + document organiser + visit notes + lab reports."""
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    kind: Mapped[str] = mapped_column(String(20))  # prescription|report|lab|scan|visit_note|aadhaar|pan|insurance|pension|other
    title: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(EncryptedText, default="")
    file_ref: Mapped[str] = mapped_column(String(120), default="")
    expires_on: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    meta: Mapped[str] = mapped_column(Text, default="{}")
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    kind: Mapped[str] = mapped_column(String(12))  # festival|birthday|vaccine|checkup|document|insurance|alarm|custom
    title: Mapped[str] = mapped_column(String(120))
    due_on: Mapped[datetime] = mapped_column(Date)
    due_time: Mapped[str] = mapped_column(String(5), default="")
    yearly: Mapped[bool] = mapped_column(Boolean, default=False)
    done: Mapped[bool] = mapped_column(Boolean, default=False)


class Message(Base):
    """Grandchild voice messages/drawings, daily 'I'm fine', call nudges."""
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    sender_id: Mapped[int] = _fk(False)
    kind: Mapped[str] = mapped_column(String(10))  # voice | drawing | text | imfine
    body: Mapped[str] = mapped_column(EncryptedText, default="")
    file_ref: Mapped[str] = mapped_column(String(120), default="")
    played: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class LifeStory(Base):
    __tablename__ = "life_stories"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    title: Mapped[str] = mapped_column(String(120))
    transcript: Mapped[str] = mapped_column(EncryptedText, default="")
    file_ref: Mapped[str] = mapped_column(String(120), default="")
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class GameScore(Base):
    __tablename__ = "game_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    game: Mapped[str] = mapped_column(String(20))
    level: Mapped[int] = mapped_column(Integer)
    pct: Mapped[int] = mapped_column(Integer)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CognitiveResult(Base):
    __tablename__ = "cognitive_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    score: Mapped[int] = mapped_column(Integer)
    max_score: Mapped[int] = mapped_column(Integer)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Refill(Base):
    __tablename__ = "refills"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"))
    channel: Mapped[str] = mapped_column(String(12), default="whatsapp")  # 1mg | pharmeasy | whatsapp
    status: Mapped[str] = mapped_column(String(16), default="pending_confirm")  # pending_confirm|confirmed|cancelled
    link: Mapped[str] = mapped_column(String(400), default="")
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    kind: Mapped[str] = mapped_column(String(10))  # sleep | steps | walk | water | meal
    value: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(10), default="manual")
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class PendingItem(Base):
    """Principle 4: OCR results, voice-logged vitals, post-visit notes and remote setup are saved ONLY after the elder confirms."""
    __tablename__ = "pending_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    kind: Mapped[str] = mapped_column(String(14))  # medicine | vital | visit_note | appointment | lab | setting
    payload: Mapped[str] = mapped_column(Text)
    readback: Mapped[str] = mapped_column(Text, default="")  # sentence read aloud for voice confirmation
    proposed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending|confirmed|rejected
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ScamReport(Base):
    __tablename__ = "scam_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    source: Mapped[str] = mapped_column(String(40), default="")
    text: Mapped[str] = mapped_column(EncryptedText, default="")
    risk: Mapped[int] = mapped_column(Integer, default=0)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CallLog(Base):
    __tablename__ = "call_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _fk()
    elder_id: Mapped[int] = _fk()
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class VideoCall(Base):
    __tablename__ = "video_calls"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    caller_id: Mapped[int] = _fk(False)
    room_url: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(10), default="ringing")  # ringing|accepted|declined|missed
    auto_answered: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    kind: Mapped[str] = mapped_column(String(14))  # bp | glucometer | oximeter | watch | speaker
    ident: Mapped[str] = mapped_column(String(60), default="")
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ServiceRequest(Base):
    """NRI mode: pay for local help (nurse, driver, groceries). The elder approves before anyone visits."""
    __tablename__ = "service_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    requester_id: Mapped[int] = _fk(False)
    kind: Mapped[str] = mapped_column(String(12))  # nurse | driver | groceries | other
    when: Mapped[datetime] = mapped_column(DateTime)
    notes: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(14), default="pending_elder")  # pending_elder|approved|declined|done
    payment_link: Mapped[str] = mapped_column(String(300), default="")
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class NomineeRequest(Base):
    __tablename__ = "nominee_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    nominee_id: Mapped[int] = _fk(False)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending|active|rejected|restored
    approvals: Mapped[str] = mapped_column(Text, default="[]")  # json [{user_id, role, at}]
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class NomineeEvent(Base):
    __tablename__ = "nominee_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("nominee_requests.id"), index=True)
    actor_id: Mapped[int] = _fk(False)
    what: Mapped[str] = mapped_column(String(200))
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Org(Base):
    __tablename__ = "orgs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(14))  # hospital|insurer|pharmacy|oldagehome|corporate|ngo|government
    code: Mapped[str] = mapped_column(String(12), unique=True)
    admin_id: Mapped[int] = _fk(False)  # the 'partner' user whose consents represent the organisation
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CommunityRoom(Base):
    __tablename__ = "community_rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    area: Mapped[str] = mapped_column(String(40), default="")
    interest: Mapped[str] = mapped_column(String(40), default="")


class CommunityPost(Base):
    __tablename__ = "community_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("community_rooms.id"), index=True)
    user_id: Mapped[int] = _fk(False)
    text: Mapped[str] = mapped_column(Text)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    reports: Mapped[int] = mapped_column(Integer, default=0)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Subscription(Base):
    __tablename__ = "subscriptions"
    elder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tier: Mapped[str] = mapped_column(String(8), default="free")  # free | family | care
    payer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ChwVisit(Base):
    __tablename__ = "chw_visits"
    id: Mapped[int] = mapped_column(primary_key=True)
    chw_id: Mapped[int] = _fk(False)
    elder_id: Mapped[int] = _fk()
    notes: Mapped[str] = mapped_column(EncryptedText, default="")
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class IvrSession(Base):
    __tablename__ = "ivr_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    elder_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    step: Mapped[int] = mapped_column(Integer, default=0)
    answers: Mapped[str] = mapped_column(Text, default="{}")
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class WellbeingCheck(Base):
    __tablename__ = "wellbeing_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _fk()
    score: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(10))
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


class DialectFeedback(Base):
    __tablename__ = "dialect_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = _fk()
    dialect: Mapped[str] = mapped_column(String(30), default="")
    heard: Mapped[str] = mapped_column(String(200))
    meant: Mapped[str] = mapped_column(String(200))
    at: Mapped[datetime] = mapped_column(DateTime, default=now)
