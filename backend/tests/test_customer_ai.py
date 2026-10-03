import pytest
from datetime import date, timedelta
from backend.app.core.database import SessionLocal
from backend.app.models.user import User, UserStatus

@pytest.fixture(scope="module", autouse=True)
def clean_customer_ai_test_state():
    db = SessionLocal()
    c = db.query(User).filter(User.email == "customer@example.com").first()
    if c and c.customer_profile:
        c.customer_profile.wallet_balance = 500.00
        c.customer_profile.grace_balance = 0.00
        c.is_frozen = False
        c.status = UserStatus.ACTIVE
    db.commit()
    db.close()
    yield

def get_auth_token(client, email, password=None):
    if password is None:
        password = "Admin@1234" if "admin" in email else "Demo@1234"
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_cash_flow_trajectory(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    res = client.get("/api/v1/customer-ai/trajectory", headers=c_headers)
    assert res.status_code == 200
    data = res.json()

    assert "daily_forecast" in data
    assert len(data["daily_forecast"]) == 30
    assert "current_balance" in data
    assert "has_deficit_alert" in data
    assert "projected_30d_end_balance" in data

    first_point = data["daily_forecast"][0]
    assert "inflow_forecast" in first_point
    assert "outflow_forecast" in first_point
    assert "projected_balance" in first_point

    # RBAC: Agent should not be able to access Customer trajectory
    a_token = get_auth_token(client, "agent@example.com")
    a_headers = {"Authorization": f"Bearer {a_token}"}
    agent_res = client.get("/api/v1/customer-ai/trajectory", headers=a_headers)
    assert agent_res.status_code == 403

def test_grace_credit_eligibility_and_advance(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    # 1. Eligibility Check
    elig_res = client.get("/api/v1/customer-ai/grace/eligibility", headers=c_headers)
    assert elig_res.status_code == 200
    elig_data = elig_res.json()

    assert 300 <= elig_data["credit_score"] <= 850
    assert elig_data["eligible"] is True
    assert elig_data["approved_limit"] >= 20.0
    assert len(elig_data["positive_factors"]) >= 1

    # Check initial balance
    me_res = client.get("/api/v1/auth/me", headers=c_headers)
    initial_wallet = me_res.json()["profile"]["wallet_balance"]

    # 2. Request Grace Overdraft Advance of 20 BDT
    req_res = client.post("/api/v1/customer-ai/grace/request", json={
        "requested_amount": 20.00
    }, headers=c_headers)

    assert req_res.status_code == 201
    loan = req_res.json()
    assert loan["requested_amount"] == 20.00
    assert loan["status"] == "APPROVED"

    # Wallet balance should have increased by 20, grace_balance = 20
    me_after = client.get("/api/v1/auth/me", headers=c_headers)
    assert me_after.json()["profile"]["wallet_balance"] == initial_wallet + 20.00
    assert me_after.json()["profile"]["grace_balance"] == 20.00

    # 3. Second request must be declined due to active loan
    declined_res = client.post("/api/v1/customer-ai/grace/request", json={
        "requested_amount": 10.00
    }, headers=c_headers)
    assert declined_res.status_code == 400
    assert declined_res.json()["error"]["code"] == "GRACE_INELIGIBLE"

def test_micro_fdr_flow(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    # 1. Get Recommendations
    rec_res = client.get("/api/v1/customer-ai/fdr/recommendation", headers=c_headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert "options" in rec_data
    assert len(rec_data["options"]) == 3  # 7d, 30d, 90d

    # 2. Open a 30-day Micro-FDR with 50.00 BDT
    me_before = client.get("/api/v1/auth/me", headers=c_headers)
    bal_before = me_before.json()["profile"]["wallet_balance"]

    fdr_res = client.post("/api/v1/customer-ai/fdr/create", json={
        "principal_amount": 50.00,
        "term_days": 30
    }, headers=c_headers)

    assert fdr_res.status_code == 201
    fdr_data = fdr_res.json()
    assert fdr_data["principal_amount"] == 50.00
    assert fdr_data["term_days"] == 30
    assert fdr_data["interest_rate_pct"] == 7.50
    assert fdr_data["status"] == "ACTIVE"
    assert fdr_data["projected_profit"] > 0

    # Wallet balance should be reduced by 50.00
    me_after = client.get("/api/v1/auth/me", headers=c_headers)
    assert me_after.json()["profile"]["wallet_balance"] == bal_before - 50.00

    # 3. List active FDR accounts
    list_res = client.get("/api/v1/customer-ai/fdr/accounts", headers=c_headers)
    assert list_res.status_code == 200
    fdrs = list_res.json()
    assert len(fdrs) >= 1
    assert any(f["id"] == fdr_data["id"] for f in fdrs)
