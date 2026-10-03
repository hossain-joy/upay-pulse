import pytest
from backend.app.core.database import SessionLocal
from backend.app.models.user import User, UserStatus
from backend.app.models.agent_ai import AgentLiquidityForecast

@pytest.fixture(scope="module", autouse=True)
def clean_agent_ai_test_state():
    db = SessionLocal()
    a = db.query(User).filter(User.email == "agent@example.com").first()
    if a and a.agent_profile:
        a.agent_profile.cash_balance = 45000.00
        a.agent_profile.float_balance = 120000.00
        a.is_frozen = False
        a.status = UserStatus.ACTIVE
    db.commit()
    db.close()
    yield

def get_auth_token(client, email, password=None):
    if password is None:
        password = "Admin@1234" if "admin" in email else "Demo@1234"
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_agent_liquidity_forecast(client):
    a_token = get_auth_token(client, "agent@example.com")
    a_headers = {"Authorization": f"Bearer {a_token}"}

    res = client.get("/api/v1/agent-ai/forecast", headers=a_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["agent_code"] == "AGT-1001"
    assert data["is_factory_zone"] is True
    assert data["location_cluster"] == "Savar Garment Zone"
    assert "daily_forecast" in data
    assert len(data["daily_forecast"]) == 7
    assert data["total_7d_predicted_cash_out"] > 0
    assert data["stockout_risk"] in ("CRITICAL", "ELEVATED", "MODERATE", "LOW")

    first_day = data["daily_forecast"][0]
    assert first_day["predicted_cash_out"] > 0
    assert first_day["recommended_float"] > 0
    assert "day_of_week" in first_day

    # Verify forecast points persisted in DB
    db = SessionLocal()
    count = db.query(AgentLiquidityForecast).count()
    assert count >= 7
    db.close()

def test_agent_liquidity_rebalancing(client):
    a_token = get_auth_token(client, "agent@example.com")
    a_headers = {"Authorization": f"Bearer {a_token}"}

    # 1. Float to Cash Rebalance
    rebal_res = client.post("/api/v1/agent-ai/rebalance", json={
        "action": "FLOAT_TO_CASH",
        "amount": 10000.00
    }, headers=a_headers)

    assert rebal_res.status_code == 200
    res_data = rebal_res.json()
    assert res_data["action"] == "FLOAT_TO_CASH"
    assert res_data["amount"] == 10000.00
    assert res_data["new_cash"] == res_data["previous_cash"] + 10000.00
    assert res_data["new_float"] == res_data["previous_float"] - 10000.00

    # 2. Cash to Float Rebalance
    rebal_res2 = client.post("/api/v1/agent-ai/rebalance", json={
        "action": "CASH_TO_FLOAT",
        "amount": 5000.00
    }, headers=a_headers)

    assert rebal_res2.status_code == 200
    res_data2 = rebal_res2.json()
    assert res_data2["new_cash"] == res_data["new_cash"] - 5000.00
    assert res_data2["new_float"] == res_data["new_float"] + 5000.00

    # 3. Excessive rebalance error check
    fail_res = client.post("/api/v1/agent-ai/rebalance", json={
        "action": "FLOAT_TO_CASH",
        "amount": 9999999.00
    }, headers=a_headers)
    assert fail_res.status_code == 400
    assert fail_res.json()["error"]["code"] == "INSUFFICIENT_FLOAT"

def test_agent_ai_rbac_isolation(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    # Customers must be rejected from AgentAI
    res = client.get("/api/v1/agent-ai/forecast", headers=c_headers)
    assert res.status_code == 403
