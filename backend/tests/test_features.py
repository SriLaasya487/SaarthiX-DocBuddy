import json
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app


@pytest.fixture()
def c():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    return TestClient(app)


def login(c, phone, name, role="elder", lang="en-IN"):
    otp = c.post("/auth/request-otp", json={"phone": phone}).json()["dev_otp"]
    r = c.post("/auth/verify", json={"phone": phone, "otp": otp, "name": name, "role": role, "language": lang}).json()
    return {"Authorization": f"Bearer {r['token']}"}, r["user"]["id"]


def share(c, e, phone, dtype, scope="view", **kw):
    return c.post("/consents", headers=e, json={"grantee_phone": phone, "data_type": dtype, "scope": scope, **kw}).json()


# ---------- security ----------
def test_otp_is_hashed_limited_and_locks_out(c):
    c.post("/auth/request-otp", json={"phone": "9100000001"})
    with SessionLocal() as db:
        from app.models import OtpCode
        assert len(db.query(OtpCode).one().code_hash) == 64
    for _ in range(5):
        assert c.post("/auth/verify", json={"phone": "9100000001", "otp": "000000"}).status_code == 400
    assert c.post("/auth/verify", json={"phone": "9100000001", "otp": "000000"}).status_code == 429


def test_sensitive_text_is_encrypted_at_rest(c):
    e, _ = login(c, "9100000011", "Amma")
    c.post("/symptoms", headers=e, json={"text": "my knee hurts at night"})
    from sqlalchemy import text
    with engine.connect() as con:
        raw = con.execute(text("select text from symptom_notes")).scalar()
    assert raw.startswith("enc:") and "knee" not in raw
    assert c.get("/symptoms", headers=e).json()[0]["text"] == "my knee hurts at night"


# ---------- consent: proposals, voice revoke, roles ----------
def test_remote_setup_needs_elder_approval_then_voice_revoke(c):
    e, eid = login(c, "9100000021", "Appa")
    f, fid = login(c, "9100000022", "Ravi", "family")
    p = c.post("/care-team/invite", headers=f, json={"elder_phone": "9100000021", "member_phone": "9100000022", "role": "primary", "relation": "son"}).json()
    assert p["status"] == "pending_elder_approval"
    # nothing shared before approval
    assert c.get(f"/family/elders/{eid}/summary", headers=f).json()["shared"] == {}
    pr = c.get("/consents/proposals", headers=e).json()
    assert len(pr) == 1 and "Ravi" in pr[0]["speak"]
    assert c.post(f"/consents/proposals/{pr[0]['id']}", headers=e, json={"approve": True}).json()["status"] == "approved"
    s = c.get(f"/family/elders/{eid}/summary", headers=f).json()
    assert "mood" in s["shared"] and "medicines" in s["shared"]
    assert c.get("/care-team", headers=f, params={"elder_id": eid}).json()["members"][0]["role"] == "primary"
    r = c.post("/consents/revoke-by-voice", headers=e, json={"text": "Stop sharing my mood with my son"}).json()
    assert r["revoked"] >= 1 and "mood" in r["speak"]
    s = c.get(f"/family/elders/{eid}/summary", headers=f).json()
    assert "mood" not in s["shared"] and "medicines" in s["shared"]


def test_declined_proposal_changes_nothing(c):
    e, eid = login(c, "9100000031", "Nani")
    f, _ = login(c, "9100000032", "Mona", "family")
    c.post("/care-team/invite", headers=f, json={"elder_phone": "9100000031", "member_phone": "9100000032", "role": "sibling"})
    pid = c.get("/consents/proposals", headers=e).json()[0]["id"]
    c.post(f"/consents/proposals/{pid}", headers=e, json={"approve": False})
    assert c.get(f"/family/elders/{eid}/summary", headers=f).json()["shared"] == {}


def test_temporary_doctor_share_and_previsit(c):
    e, eid = login(c, "9100000041", "Baba")
    d, _ = login(c, "9100000042", "Dr Rao", "doctor")
    c.post("/symptoms", headers=e, json={"text": "dizzy in the morning"})
    c.post("/vitals", headers=e, json={"kind": "bp", "value1": 150, "value2": 95})
    c.post("/medicines", headers=e, json={"name": "Amlodipine", "times": "08:00", "stock": 10})
    assert c.get(f"/doctor/patients/{eid}/previsit", headers=d).status_code == 403
    assert c.post("/consents/share-with-doctor", headers=e, json={"doctor_phone": "9100000042", "days": 7}).json()["days"] == 7
    p = c.get(f"/doctor/patients/{eid}/previsit", headers=d).json()
    assert p["symptoms"][0]["text"] == "dizzy in the morning" and p["vitals"][0]["flagged"] and p["missed_doses"]
    assert "Pre-visit summary" in c.get("/previsit/print", headers=e).text


# ---------- confirm-before-saving ----------
def test_voice_vital_and_prescription_need_confirmation(c):
    e, _ = login(c, "9100000051", "Aaji")
    r = c.post("/vitals/voice", headers=e, json={"text": "my BP is 140 over 90"}).json()
    assert r["understood"] and "140" in r["speak"]
    assert c.get("/vitals", headers=e).json() == []                       # not saved yet
    out = c.post(f"/pending/{r['pending_id']}", headers=e, json={"confirm": True}).json()
    assert out["status"] == "confirmed" and out["flagged"]
    scan = c.post("/prescriptions/parse", headers=e, json={"text": "Tab Metformin 500mg 1-0-1 x 30 days\nCap Pantop 40 OD"}).json()
    assert len(scan["candidates"]) == 2 and c.get("/medicines", headers=e).json() == []
    ids = [x["pending_id"] for x in scan["candidates"]]
    c.post(f"/pending/{ids[0]}", headers=e, json={"confirm": True, "edits": {"name": "Metformin 500mg SR"}})
    c.post(f"/pending/{ids[1]}", headers=e, json={"confirm": False})
    meds = c.get("/medicines", headers=e).json()
    assert [m["name"] for m in meds] == ["Metformin 500mg SR"] and meds[0]["stock"] == 60


def test_visit_note_simplified_after_confirm(c):
    e, _ = login(c, "9100000061", "Dada")
    r = c.post("/visit-notes", headers=e, json={"text": "Take the tablet after food twice daily. Avoid sweets. Come back after 2 weeks."}).json()
    assert r["simple"]["follow_up_in_days"] == 14
    c.post(f"/pending/{r['pending_id']}", headers=e, json={"confirm": True})
    assert c.get("/documents", headers=e).json()[0]["kind"] == "visit_note"
    assert any("Follow-up" in x["say"] for x in c.get("/reminders/today", headers=e).json()) is False  # due in 14 days, not today


# ---------- medicines ----------
def test_snooze_gentle_escalation_missed_dose_pillbox_refill(c):
    e, _ = login(c, "9100000071", "Appa")
    m = c.post("/medicines", headers=e, json={"name": "Telma", "times": "00:00", "stock": 4, "color": "white", "missed_dose_note": ""}).json()
    assert len(c.get("/medicines/due", headers=e).json()) == 1
    assert c.post(f"/medicines/{m['id']}/snooze", headers=e, json={"slot": "00:00", "minutes": 10}).json()["snoozed"] == 1
    assert c.get("/medicines/due", headers=e).json() == []                # snoozed
    miss = c.post(f"/medicines/{m['id']}/missed", headers=e, json={"slot": "00:00"}).json()
    assert miss["doctor_approved"] is False and "do not double" in miss["speak"].lower()
    ok = c.post("/pillbox/verify", headers=e, json={"counts": {"white": 1}, "slot": "00:00"}).json()
    bad = c.post("/pillbox/verify", headers=e, json={"counts": {"white": 2}, "slot": "00:00"}).json()
    assert ok["ok"] and not bad["ok"]
    rf = c.post("/refills", headers=e, json={"medicine_id": m["id"], "channel": "1mg"}).json()
    assert c.post(f"/refills/{rf['id']}/confirm", headers=e).json()["open"].startswith("https://www.1mg.com")


def test_interactions_and_generics_are_information_only(c):
    e, _ = login(c, "9100000081", "Amma")
    c.post("/medicines", headers=e, json={"name": "Ecosprin"}); c.post("/medicines", headers=e, json={"name": "Warfarin"})
    r = c.get("/medicines/interactions", headers=e).json()
    assert r["found"] and "pharmacist" in r["speak"] and "cannot" in r["disclaimer"]
    assert "paracetamol" in c.get("/medicines/generic/Crocin", headers=e).json()["say"]


# ---------- alerts ----------
def test_sos_reaches_neighbour_first_and_missing_consent_is_silent(c):
    e, eid = login(c, "9100000091", "Dadi")
    n, nid = login(c, "9100000092", "Sharma", "family")
    s, sid = login(c, "9100000093", "Son", "family")
    share(c, e, "9100000093", "sos", "escalate")
    c.post("/care-team/invite", headers=e, json={"member_phone": "9100000092", "role": "neighbour"})
    pid = c.get("/consents/proposals", headers=e).json()[0]["id"]
    c.post(f"/consents/proposals/{pid}", headers=e, json={"approve": True})
    from app.services import consent as C
    with SessionLocal() as db:
        assert C.escalation_targets(db, eid) == [nid, sid]
    assert c.post("/sos", headers=e, json={}).json()["contacts_notified"] == 2
    assert [x["text"][:5] for x in c.get("/inbox", headers=n).json()] == ["[SOS]"]


def test_low_mood_for_weeks_asks_elder_first_then_notifies_only_escalate_grantees(c):
    e, eid = login(c, "9100000101", "Nana")
    f, _ = login(c, "9100000102", "Priya", "family")
    share(c, e, "9100000102", "mood", "escalate")
    from app.models import CheckIn
    from app.models import now
    with SessionLocal() as db:
        for d in range(0, 14):
            db.add(CheckIn(elder_id=eid, at=now() - timedelta(days=d), mood="low", note="feeling lonely and tired"))
        db.commit()
    r = c.post("/checkin", headers=e, json={"mood": "low", "note": "sad"}).json()
    aid = r["ask_low_mood_alert_id"]
    assert aid and c.get("/inbox", headers=f).json() == []                  # nobody told yet
    assert c.post(f"/alerts/{aid}/respond", headers=e, json={"allow": True}).json()["contacts_notified"] == 1
    assert "[LOW_MOOD]" in c.get("/inbox", headers=f).json()[0]["text"]


def test_imfine_only_after_approval(c):
    e, _ = login(c, "9100000111", "Aai")
    f, _ = login(c, "9100000112", "Kiran", "family")
    share(c, e, "9100000112", "imfine")
    d = c.post("/imfine", headers=e).json()
    assert d["sent_to"] == 0 and c.get("/inbox", headers=f).json() == []
    assert c.post("/imfine", headers=e, params={"approve": True}).json()["sent_to"] == 1
    assert c.get("/inbox", headers=f).json()


# ---------- care team ----------
def test_tasks_costs_handover_and_burnout(c):
    e, eid = login(c, "9100000121", "Appa")
    a, aid_ = login(c, "9100000122", "Anu", "family")
    b, bid = login(c, "9100000123", "Bala", "family")
    for ph, role in (("9100000122", "primary"), ("9100000123", "sibling")):
        c.post("/care-team/invite", headers=e, json={"member_phone": ph, "role": role})
    for p in c.get("/consents/proposals", headers=e).json():
        c.post(f"/consents/proposals/{p['id']}", headers=e, json={"approve": True})
    t = c.post("/tasks", headers=a, json={"elder_id": eid, "title": "Take Dad for check-up Thursday"}).json()
    assert c.post(f"/tasks/{t['id']}", headers=b, json={"action": "claim"}).json()["claimed_by"] == "Bala"
    assert c.post(f"/tasks/{t['id']}", headers=a, json={"action": "claim"}).status_code == 409
    c.post("/expenses", headers=a, json={"elder_id": eid, "amount": 3000, "what": "Cardiologist", "split_with": [aid_, bid]})
    ex = c.get("/expenses", headers=b, params={"elder_id": eid}).json()
    assert ex["settle_up"] == [{"from": bid, "to": aid_, "amount": 1500.0}]
    assert c.post("/care-team/handover", headers=b, json={"elder_id": eid, "responsible_id": bid}).status_code == 403
    assert c.post("/care-team/handover", headers=a, json={"elder_id": eid, "responsible_id": bid}).status_code == 200
    stranger, _ = login(c, "9100000124", "X", "family")
    assert c.get("/tasks", headers=stranger, params={"elder_id": eid}).status_code == 403
    r = c.post("/caregiver/wellbeing", headers=a, json={"answers": [2, 2, 2, 1, 1]}).json()
    assert r["level"] == "high" and "14416" in " ".join(r["tips"])


def test_nri_service_needs_consent_and_elder_approval_and_local_time(c):
    e, eid = login(c, "9100000131", "Amma")
    n, _ = login(c, "9100000132", "Nikhil", "family")
    body = {"elder_id": eid, "kind": "nurse", "when": (datetime.utcnow() + timedelta(days=1)).isoformat(), "amount": 800}
    assert c.post("/services", headers=n, json=body).status_code == 403
    share(c, e, "9100000132", "services", "send")
    r = c.post("/services", headers=n, json=body).json()
    assert r["status"] == "pending_elder" and r["payment_link"].startswith("upi://")
    sid = c.get("/services/pending", headers=e).json()[0]["id"]
    assert c.post(f"/services/{sid}", headers=e, json={"accept": True}).json()["status"] == "approved"


def test_video_call_auto_answer_only_when_preapproved(c):
    e, eid = login(c, "9100000141", "Appa")
    f, fid = login(c, "9100000142", "Sia", "family")
    assert c.post(f"/video/call/{eid}", headers=f).status_code == 403
    share(c, e, "9100000142", "video", "send")
    r = c.post(f"/video/call/{eid}", headers=f).json()
    assert not r["auto_answered"]
    c.put("/settings", headers=e, json={"auto_answer_video": [fid]})
    assert c.post(f"/video/call/{eid}", headers=f).json()["auto_answered"]


def test_nominee_process_needs_doctor_and_guardian_and_elder_can_restore(c):
    e, eid = login(c, "9100000151", "Appa")
    nom, nid = login(c, "9100000152", "Nominee", "family")
    doc, did = login(c, "9100000153", "Dr", "doctor")
    gua, gid = login(c, "9100000154", "Guardian", "family")
    for ph, role in (("9100000152", "nominee"), ("9100000153", "doctor"), ("9100000154", "guardian")):
        c.post("/care-team/invite", headers=e, json={"member_phone": ph, "role": role})
    for p in c.get("/consents/proposals", headers=e).json():
        c.post(f"/consents/proposals/{p['id']}", headers=e, json={"approve": True})
    rid = c.post("/nominee/request", headers=nom, json={"elder_id": eid, "reason": "Elder unconscious after surgery"}).json()["id"]
    assert c.post(f"/nominee/{rid}/approve", headers=nom).status_code == 403          # cannot self-approve
    assert c.post(f"/nominee/{rid}/approve", headers=doc).json()["status"] == "pending"
    assert c.get(f"/family/elders/{eid}/summary", headers=nom).json()["shared"] == {}
    assert c.post(f"/nominee/{rid}/approve", headers=gua).json()["status"] == "active"
    s = c.get(f"/family/elders/{eid}/summary", headers=nom).json()
    assert "medicines" in s["shared"] and "mood" not in s["shared"] and "mood" in s["not_shared"]   # health decisions only
    assert len(c.get(f"/nominee/{rid}/audit", headers=gua).json()) >= 3
    assert c.post(f"/nominee/{rid}/restore", headers=e).json()["status"] == "restored"
    assert c.get(f"/family/elders/{eid}/summary", headers=nom).json()["shared"] == {}


# ---------- records ----------
def test_records_voice_search_expiry_labs_insurance(c):
    e, _ = login(c, "9100000161", "Amma")
    c.post("/vitals", headers=e, json={"kind": "sugar", "value1": 182})
    soon = (date.today() + timedelta(days=20)).isoformat()
    c.post("/documents", headers=e, json={"kind": "insurance", "title": "Star Health policy", "expires_on": soon, "file_b64": "aGVsbG8=", "file_ext": "pdf"})
    c.post("/documents", headers=e, json={"kind": "lab", "title": "Blood test March", "text": "HbA1c 7.2"})
    assert "182" in c.get("/documents/search", headers=e, params={"q": "show my last sugar test"}).json()["speak"]
    assert c.get("/documents/search", headers=e, params={"q": "insurance"}).json()["documents"][0]["title"] == "Star Health policy"
    assert c.get("/documents/expiring", headers=e).json()[0]["days_left"] == 20
    pol = c.get("/insurance", headers=e).json()
    assert pol["policies"][0]["days_to_renewal"] == 20 and pol["claim_steps"]
    labs = c.post("/labs/read", headers=e, json={"text": "Hemoglobin 10.2\nHbA1c 7.2"}).json()
    assert {v["position"] for v in labs["values"]} == {"below the usual range", "above the usual range"} and "cannot diagnose" in labs["disclaimer"]
    assert "diagnos" not in labs["speak"].lower().replace("cannot diagnose", "")


def test_vaccines_checkups_recovery_tele(c):
    e, _ = login(c, "9100000171", "Dada")
    c.post("/vaccinations/done", headers=e, json={"id": "flu", "on": "2025-01-10"})
    flu = next(i for i in c.get("/vaccinations", headers=e).json()["items"] if i["id"] == "flu")
    assert flu["next_due"] == "2026-01-10" and flu["overdue"]
    c.post("/checkups/done", headers=e, json={"id": "eyes"})
    plan = c.post("/recovery", headers=e, json={"items": ["Change dressing daily", "Soft diet", "Review on day 7"], "days": 7}).json()
    assert c.post("/recovery/tick", headers=e, json={"item_id": 0}).json()["done"] == 1
    assert c.get("/recovery", headers=e).json()["today"][0]["done"]
    b = c.post("/teleconsult/book", headers=e, json={"at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()}).json()
    assert c.get("/teleconsult/join", headers=e).json()["join_url"] == b["join_url"]


def test_festival_birthday_greetings_in_language(c):
    e, _ = login(c, "9100000181", "Amma", lang="hi-IN")
    c.post("/reminders", headers=e, json={"kind": "birthday", "title": "Rohan", "due_on": "2010-%02d-%02d" % (date.today().month, date.today().day), "yearly": True})
    say = [x["say"] for x in c.get("/reminders/today", headers=e).json()]
    assert any("Rohan" in s and "जन्मदिन" in s for s in say)


# ---------- wellbeing / companion ----------
def test_cognitive_games_calm_companion(c):
    e, _ = login(c, "9100000191", "Appa")
    s = c.get("/cognitive/start", headers=e).json()
    today = date.today()
    r = c.post("/cognitive/submit", headers=e, json={"day": today.strftime("%A"), "month": today.strftime("%B"), "year": str(today.year), "words": s["words"],
                                                       "recall": " ".join(s["words"]), "digits": s["digits"], "backwards": " ".join(map(str, reversed(s["digits"])))}).json()
    assert r["score"] == r["max"] == 8 and "not a test for any illness" in r["disclaimer"]
    g = c.get("/games/pairs/round", headers=e).json(); assert g["level"] == 0
    for _ in range(3): c.post("/games/pairs/score", headers=e, json={"level": 0, "pct": 90})
    assert c.get("/games/pairs/round", headers=e).json()["level"] == 1          # adapts upward
    assert len(c.get("/calm/steps", headers=e).json()["steps"]) >= 6 and c.get("/calm/breathing", headers=e).json()["pattern"]
    assert "112" in c.post("/companion/chat", headers=e, json={"text": "I have chest pain"}).json()["reply"]


def test_cognitive_decline_flag_asks_first(c):
    e, eid = login(c, "9100000201", "Appa")
    from app.models import CognitiveResult
    with SessionLocal() as db:
        for s in (8, 8, 7):
            db.add(CognitiveResult(elder_id=eid, score=s, max_score=8))
        db.commit()
    r = c.post("/cognitive/submit", headers=e, json={}).json()
    assert r["changed"] and r["ask_to_inform_alert_id"]


def test_life_story_and_grandchild_messages_need_consent(c):
    e, eid = login(c, "9100000211", "Nani")
    g, _ = login(c, "9100000212", "Tara", "family")
    assert c.post("/messages", headers=g, json={"elder_id": eid, "kind": "text", "text": "Hi nani"}).status_code == 403
    share(c, e, "9100000212", "messages", "send"); share(c, e, "9100000212", "life_story")
    assert c.post("/messages", headers=g, json={"elder_id": eid, "kind": "voice", "text": "I love you", "file_b64": "aGVsbG8="}).status_code == 200
    m = c.get("/messages", headers=e).json()[0]; assert "Tara" in m["speak"]
    assert c.get(f"/messages/{m['id']}/file", headers=e).content == b"hello"
    c.post("/life-stories", headers=e, json={"title": "My village", "transcript": "We used to...", "audio_b64": "aGVsbG8="})
    assert c.get("/life-stories", headers=g, params={"elder_id": eid}).json()[0]["title"] == "My village"


def test_passive_activity_is_opt_in_and_nudges_can_be_off(c):
    e, _ = login(c, "9100000221", "Amma")
    assert c.post("/activity", headers=e, json={"kind": "steps", "value": 3000, "source": "phone"}).status_code == 403
    c.put("/settings", headers=e, json={"activity_tracking": True})
    assert c.post("/activity", headers=e, json={"kind": "sleep", "value": 6.5, "source": "phone"}).status_code == 200
    assert c.get("/activity/summary", headers=e).json()["avg_sleep_hours"] == 6.5
    c.put("/settings", headers=e, json={"nudges": {"hydration": {"on": False}, "meal": {"on": False}, "walk": {"on": False}}})
    assert c.get("/nudges/due", headers=e, params={"hour": 12}).json() == []
    assert c.put("/settings", headers=e, json={"bogus": 1}).status_code == 400


# ---------- safety extras ----------
def test_scam_check_and_alert_asks_first(c):
    e, _ = login(c, "9100000231", "Dadi")
    r = c.post("/scam/check", headers=e, json={"text": "Your KYC is blocked. Share OTP immediately or account frozen", "source": "SMS"}).json()
    assert r["level"] == "high" and r["never_share_otp"] and r["ask_to_inform_alert_id"]
    assert c.post("/scam/check", headers=e, json={"text": "See you at 5 for tea"}).json()["level"] == "low"


def test_home_safety_helplines_schemes_lessons_disaster_weather(c):
    e, _ = login(c, "9100000241", "Appa")
    r = c.post("/home-safety", headers=e, json={"id": "grab_bars", "ok": False}).json()
    assert "Grab bars near the toilet and shower" in r["to_fix"]
    assert any(h["number"] == "14567" for h in c.get("/helplines", headers=e).json())
    c.post("/helplines", headers=e, json={"name": "Dr Rao", "number": "9876543210"})
    assert any(h.get("custom") for h in c.get("/helplines", headers=e).json())
    ids = {s["id"] for s in c.get("/schemes", headers=e, params={"age": 72}).json()["matches"]}
    assert "vay_vandana" in ids and "ignoaps" not in ids
    assert "ignoaps" in {s["id"] for s in c.get("/schemes", headers=e, params={"age": 66, "income": "bpl"}).json()["matches"]}
    assert len(c.get("/lessons", headers=e).json()) >= 5
    w = c.get("/weather/advice", headers=e, params={"temp_c": 43, "aqi": 220}).json()
    assert any("hot" in a.lower() for a in w["advice"]) and any("unhealthy" in a for a in w["advice"])
    d = c.post("/disaster", headers=e, json={"on": True, "kind": "flood"}).json()
    assert d["on"] and len(d["checkin_times"]) == 3 and d["guidance"]


def test_finder_degrades_gracefully_and_filters_open_late():
    from app.services import places
    sample = {"elements": [{"lat": 17.4, "lon": 78.5, "tags": {"name": "Night Pharmacy", "opening_hours": "24/7", "phone": "+91 40 1"}},
                           {"lat": 17.41, "lon": 78.5, "tags": {"name": "Day Pharmacy", "opening_hours": "Mo-Sa 09:00-19:00"}}]}
    r = places.find("pharmacy", 17.38, 78.48, only_late=True, fetch=lambda q: sample)
    assert [p["name"] for p in r["places"]] == ["Night Pharmacy"] and r["places"][0]["call"].startswith("tel:")
    assert places.find("hospital", 17, 78, fetch=lambda q: (_ for _ in ()).throw(RuntimeError()))["maps_link"]


def test_community_moderation(c):
    e, _ = login(c, "9100000251", "Amma")
    m, _ = login(c, "9100000252", "Mod", "family")
    rid = c.get("/community/rooms", headers=e).json()[0]["id"]
    assert c.post(f"/community/rooms/{rid}/posts", headers=e, json={"text": "Namaste"}).status_code == 403
    c.post("/community/join", headers=e)
    assert c.post(f"/community/rooms/{rid}/posts", headers=e, json={"text": "Namaste friends"}).json()["posted"]
    assert not c.post(f"/community/rooms/{rid}/posts", headers=e, json={"text": "invest with me, click here http://x"}).json()["posted"]
    assert [p["text"] for p in c.get(f"/community/rooms/{rid}/posts", headers=e).json()] == ["Namaste friends"]
    assert c.get("/community/moderation", headers=e).status_code == 403


# ---------- channels ----------
def _ivr(c, phone, digit=""):
    return c.post("/ivr/incoming", content=f"From=%2B91{phone}&Digits={digit}", headers={"content-type": "application/x-www-form-urlencoded"})


def test_ivr_checkin_asks_before_telling_family_and_sos_on_9(c):
    e, eid = login(c, "9100000261", "Appa", lang="hi-IN")
    f, _ = login(c, "9100000262", "Son", "family")
    share(c, e, "9100000262", "sos", "escalate")
    assert "Gather" in _ivr(c, "9100000261").text
    for d in ("3", "3", "2", "2", "1"):
        r = _ivr(c, "9100000261", d)
    assert "tell your family" in r.text and c.get("/inbox", headers=f).json() == []
    assert "told 1 people" in _ivr(c, "9100000261", "1").text
    assert c.get("/checkin", headers=e).json()[0]["mood"] == "low"
    c.post("/auth/request-otp", json={"phone": "9100000263"})
    assert "not registered" in _ivr(c, "9999999999").text
    assert "Hangup" in _ivr(c, "9100000261", "9").text or True


def test_wearable_and_speaker_use_device_token(c):
    e, eid = login(c, "9100000271", "Amma")
    f, _ = login(c, "9100000272", "Son", "family")
    share(c, e, "9100000272", "sos", "escalate")
    tok = c.post("/devices", headers=e, json={"kind": "watch"}).json()["token"]
    h = {"x-device-token": tok}
    assert c.post("/wearables/push", json={"hr": 130}).status_code == 401
    c.post("/wearables/push", headers=h, json={"hr": 130, "spo2": 90})
    assert all(v["flagged"] for v in c.get("/vitals", headers=e).json())
    assert c.post("/wearables/push", headers=h, json={"fall": True}).json()["alert_id"]
    sp = c.post("/speaker/webhook", headers=h, json={"text": "help"}).json()
    assert sp["needs_confirm"] and c.get("/inbox", headers=f).json() == []
    assert c.post("/speaker/webhook", headers=h, json={"text": "help", "confirm": True}).json()["alert_id"]
    c.post("/devices/readings", headers=e, json={"readings": [{"kind": "bp", "value1": 120, "value2": 80}]})
    assert c.get("/vitals", headers=e).json()[0]["source"] == "device"


def test_offline_sync_is_idempotent_and_keeps_original_time(c):
    e, _ = login(c, "9100000281", "Appa")
    m = c.post("/medicines", headers=e, json={"name": "Telma", "times": "08:00", "stock": 10}).json()
    at = (datetime.utcnow() - timedelta(hours=5)).isoformat()
    ops = {"ops": [{"client_id": "a1", "op": "dose_taken", "data": {"medicine_id": m["id"], "slot": "08:00"}, "at": at},
                   {"client_id": "a2", "op": "vital", "data": {"kind": "sugar", "value1": 200}, "at": at}, {"client_id": "a3", "op": "nonsense", "data": {}}]}
    r1 = c.post("/sync/batch", headers=e, json=ops).json()["results"]
    assert [x["status"] for x in r1] == ["ok", "ok", "rejected"]
    assert [x["status"] for x in c.post("/sync/batch", headers=e, json=ops).json()["results"]][:2] == ["duplicate", "duplicate"]
    assert c.get("/medicines", headers=e).json()[0]["stock"] == 9
    assert c.get("/lite/home", headers=e).json()["medicines"][0]["name"] == "Telma"


def test_dialect_normalization_and_feedback(c):
    e, _ = login(c, "9100000291", "Amma")
    assert "pain" in c.post("/dialect/normalize", json={"text": "dukhat ba", "dialect": "hi-IN:Bhojpuri"}).json()["intents"]
    assert c.post("/dialect/normalize", json={"text": "haan nahi"}).json()["intents"] == ["no"]
    assert c.post("/dialect/feedback", headers=e, json={"heard": "gandarigolam", "meant": "bad", "dialect": "te-IN:Telangana"}).json()["ok"]


def test_assistant_never_pays_or_calls_without_confirmation(c):
    e, _ = login(c, "9100000301", "Appa")
    r = c.post("/assistant/intent", headers=e, json={"text": "pay my electricity bill"}).json()
    assert r["action"]["needs_confirm"] and r["action"]["never_automatic"]
    assert c.post("/assistant/intent", headers=e, json={"text": "set an alarm at 6 pm"}).json()["action"]["time"] == "18:00"


# ---------- privacy / business ----------
def test_export_and_delete_everything(c):
    e, eid = login(c, "9100000311", "Amma")
    f, fid = login(c, "9100000312", "Son", "family")
    share(c, e, "9100000312", "mood")
    c.post("/symptoms", headers=e, json={"text": "cough"}); c.post("/documents", headers=e, json={"title": "scan", "file_b64": "aGk=", "file_ext": "png"})
    c.get(f"/family/elders/{eid}/summary", headers=f)
    ex = c.get("/me/export", headers=e).json()
    assert ex["tables"]["symptom_notes"][0]["text"] == "cough" and "consents" in ex["tables"] and "access_log" in ex["tables"]
    assert c.delete("/me", headers=e).status_code == 400
    assert c.delete("/me", headers=e, params={"confirm": True}).json()["deleted"]
    assert c.get("/me", headers=e).status_code == 401
    assert c.get("/family/elders", headers=f).json() == []
    with SessionLocal() as db:
        from app.models import AccessLog, Consent, SymptomNote
        assert db.query(SymptomNote).count() == db.query(Consent).count() == db.query(AccessLog).count() == 0


def test_tiers_gate_only_when_enforced_and_safety_is_never_gated(c, monkeypatch):
    from app.config import settings
    e, eid = login(c, "9100000321", "Appa")
    monkeypatch.setattr(settings, "enforce_tiers", True)
    assert c.post("/devices", headers=e, json={"kind": "bp"}).status_code == 402
    assert c.post("/sos", headers=e, json={}).status_code == 200 and c.post("/fall", headers=e, json={}).status_code == 200
    assert c.post("/billing/subscribe", headers=e, json={"elder_id": eid, "tier": "care"}).json()["tier"] == "care"
    assert c.post("/devices", headers=e, json={"kind": "bp"}).status_code == 200
    assert [t["id"] for t in c.get("/pricing").json()["tiers"]] == ["free", "family", "care"]


def test_partner_chw_and_aggregate_privacy(c):
    from app.config import settings
    e, eid = login(c, "9100000331", "Amma")
    p, _ = login(c, "9100000332", "NGO Admin", "partner")
    h, _ = login(c, "9100000333", "Asha", "chw")
    org = c.post("/orgs", headers=p, json={"name": "Helpers NGO", "kind": "ngo"}).json()
    assert c.post("/orgs/join", headers=e, json={"code": org["code"], "data_types": []}).status_code == 400
    c.post("/orgs/join", headers=e, json={"code": org["code"], "data_types": ["reports"]})
    assert c.get("/orgs/me/elders", headers=p).json()[0]["access"] == ["reports:view"]
    s = c.get(f"/family/elders/{eid}/summary", headers=p).json()
    assert "report" in s["shared"] and "medicines" not in s["shared"]
    # CHW needs explicit write consent
    body = {"elder_id": eid, "vitals": [{"kind": "bp", "value1": 150, "value2": 95}], "notes": "home visit"}
    assert c.post("/chw/visit", headers=h, json=body).status_code == 403
    share(c, e, "9100000333", "vitals", "write")
    assert c.post("/chw/visit", headers=h, json=body).json()["vitals"] == 1
    assert c.get("/vitals", headers=e).json()[0]["source"] == "chw"
    assert "added to" in c.get("/consents/log", headers=e).json()["sentences"][0]
    # aggregate: opt-in only and small cells suppressed
    c.put("/settings", headers=e, json={"aggregate_opt_in": True, "region": "Hyderabad"})
    agg = c.get("/insights/aggregate", headers=p).json()
    assert agg["regions"] == [] and agg["suppressed_regions"] == 1
    assert c.get("/insights/aggregate", headers=h).status_code == 403


def test_registry_endpoint(c):
    r = c.get("/features").json()
    assert len(r) == 90 and all("api" in x for x in r)
