import pytest
from backend.app.core.database import SessionLocal
from backend.app.models.user import User, UserStatus
from backend.app.models.voice import VoiceCoachSession

@pytest.fixture(scope="module", autouse=True)
def clean_voice_coach_test_state():
    db = SessionLocal()
    c = db.query(User).filter(User.email == "customer@example.com").first()
    if c and c.customer_profile:
        c.customer_profile.wallet_balance = 500.00
        c.customer_profile.grace_balance = 0.00
        c.is_frozen = False
        c.status = UserStatus.ACTIVE
    db.query(VoiceCoachSession).delete()
    db.commit()
    db.close()
    yield

def get_auth_token(client, email, password=None):
    if password is None:
        password = "Admin@1234" if "admin" in email else "Demo@1234"
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_voice_coach_balance_inquiry(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    payload = {
        "query": "আমার অ্যাকাউন্টে কত টাকা ব্যালেন্স আছে?",
        "language": "bn"
    }

    res = client.post("/api/v1/customer-ai/voice-coach/chat", json=payload, headers=c_headers)
    assert res.status_code == 200
    data = res.json()

    assert "session_id" in data
    assert data["intent"] == "BALANCE_INQUIRY"
    assert "৳" in data["response_bangla"] or "টাকা" in data["response_bangla"]
    assert data["latency_ms"] < 250.0  # Fast sub-250ms deterministic local inference
    assert data["context_summary"]["wallet_balance"] == 500.0

def test_voice_coach_grace_loan_inquiry(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    payload = {
        "query": "আমি কি এখনই কোনো জরুরি গ্রেস লোন নিতে পারব?",
        "language": "bn"
    }

    res = client.post("/api/v1/customer-ai/voice-coach/chat", json=payload, headers=c_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "GRACE_ELIGIBILITY"
    assert "উপায় গ্রেস" in data["response_bangla"] or "upay Grace" in data["response_bangla"]
    assert data["context_summary"]["grace_limit"] >= 20.0

def test_voice_coach_micro_fdr_inquiry(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    payload = {
        "query": "আমার অলস টাকার জন্য কোনো ডিপিএস বা এফডিআর সঞ্চয় সুবিধা আছে কি?",
        "language": "bn"
    }

    res = client.post("/api/v1/customer-ai/voice-coach/chat", json=payload, headers=c_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "MICRO_FDR"
    assert "৮.৫০%" in data["response_bangla"] or "মুনাফা" in data["response_bangla"]

def test_voice_coach_history_and_persistence(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    res = client.get("/api/v1/customer-ai/voice-coach/history", headers=c_headers)
    assert res.status_code == 200
    history = res.json()

    # Should contain the 3 interactions from above
    assert len(history) == 3
    first_item = history[0]
    assert "query_text" in first_item
    assert "response_bangla" in first_item
    assert "latency_ms" in first_item

    # Verify DB persistence
    db = SessionLocal()
    db_count = db.query(VoiceCoachSession).count()
    assert db_count == 3
    db.close()

def test_voice_coach_rbac_isolation(client):
    a_token = get_auth_token(client, "agent@example.com")
    a_headers = {"Authorization": f"Bearer {a_token}"}

    # Agents are not customers, so they should be blocked with 403
    res = client.post("/api/v1/customer-ai/voice-coach/chat", json={"query": "আমার ব্যালেন্স"}, headers=a_headers)
    assert res.status_code == 403
