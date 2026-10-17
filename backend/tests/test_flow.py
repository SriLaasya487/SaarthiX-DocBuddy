import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    return TestClient(app)


def login(c, phone, name, role):
    otp = c.post("/auth/request-otp", json={"phone": phone}).json()["dev_otp"]
    r = c.post("/auth/verify", json={"phone": phone, "otp": otp, "name": name, "role": role}).json()
    return {"Authorization": f"Bearer {r['token']}"}, r["user"]["id"]


def test_consent_gate_and_audit(client):
    e, eid = login(client, "9000000001", "Amma", "elder")
    f, _ = login(client, "9000000002", "Ravi", "family")
    client.post("/checkin", headers=e, json={"mood": "good"})
    # nothing shared yet
    s = client.get(f"/family/elders/{eid}/summary", headers=f).json()
    assert s["shared"] == {} and "mood" in s["not_shared"]
    # elder shares mood only
    g = client.post("/consents", headers=e, json={"grantee_phone": "9000000002", "data_type": "mood"}).json()
    s = client.get(f"/family/elders/{eid}/summary", headers=f).json()
    assert "mood" in s["shared"] and "medicines" not in s["shared"]
    # spoken audit log
    assert "Ravi saw your mood" in client.get("/consents/log", headers=e).json()["sentences"][0]
    # revoke in one call
    client.delete(f"/consents/{g['id']}", headers=e)
    assert client.get(f"/family/elders/{eid}/summary", headers=f).json()["shared"] == {}


def test_help_asks_elder_first(client):
    e, eid = login(client, "9000000011", "Appa", "elder")
    login(client, "9000000012", "Sita", "family")
    client.post("/consents", headers=e, json={"grantee_phone": "9000000012", "data_type": "sos", "scope": "escalate"})
    r = client.post("/checkin", headers=e, json={"mood": "okay", "needs_help": True}).json()
    aid = r["ask_to_inform_family_alert_id"]
    assert client.get("/alerts", headers=e).json()[0]["status"] == "pending_elder"
    assert client.post(f"/alerts/{aid}/respond", headers=e, json={"allow": False}).json()["status"] == "declined"


def test_sos_only_to_approved(client):
    e, _ = login(client, "9000000021", "Dadi", "elder")
    login(client, "9000000022", "Neha", "family")
    assert client.post("/sos", headers=e, json={}).json()["contacts_notified"] == 0
    client.post("/consents", headers=e, json={"grantee_phone": "9000000022", "data_type": "sos", "scope": "escalate"})
    assert client.post("/sos", headers=e, json={}).json()["contacts_notified"] == 1


def test_fall_escalates_when_unanswered(client, monkeypatch):
    from app.config import settings
    from app.db import SessionLocal
    from app.services.alerts import process_expired
    monkeypatch.setattr(settings, "fall_response_seconds", -1)
    e, _ = login(client, "9000000031", "Nana", "elder")
    login(client, "9000000032", "Om", "family")
    client.post("/consents", headers=e, json={"grantee_phone": "9000000032", "data_type": "sos", "scope": "escalate"})
    client.post("/fall", headers=e, json={})
    with SessionLocal() as db:
        assert process_expired(db) == 1
    assert client.get("/alerts", headers=e).json()[0]["status"] == "sent"


def test_doctor_suggestion_never_diagnoses(client):
    e, _ = login(client, "9000000041", "Baba", "elder")
    r = client.post("/doctor/suggest", headers=e, json={"symptom": "my knee hurts"}).json()
    assert r["doctor"].startswith("Orthopaedic") and "cannot diagnose" in r["disclaimer"]


def test_vitals_flag_and_medicine_stock(client):
    e, _ = login(client, "9000000051", "Aaji", "elder")
    assert client.post("/vitals", headers=e, json={"kind": "bp", "value1": 150, "value2": 95}).json()["flagged"]
    m = client.post("/medicines", headers=e, json={"name": "Metformin", "tablets": 1, "times": "00:00", "stock": 5}).json()
    assert len(client.get("/medicines/due", headers=e).json()) == 1
    assert client.post(f"/medicines/{m['id']}/taken", headers=e, json={"slot": "00:00"}).json()["stock"] == 4
    assert client.get("/medicines/due", headers=e).json() == []
