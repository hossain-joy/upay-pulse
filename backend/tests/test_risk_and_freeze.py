import pytest

def get_auth_token(client, email, password="Demo@1234"):
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_realtime_risk_evaluation_endpoint(client):
    c_token = get_auth_token(client, "customer@example.com")
    headers = {"Authorization": f"Bearer {c_token}"}

    # 1. Normal transfer evaluation
    norm_res = client.post("/api/v1/risk/evaluate", json={
        "amount": 250.00,
        "transaction_type": "SEND_MONEY",
        "velocity_10m": 1
    }, headers=headers)
    assert norm_res.status_code == 200
    norm_data = norm_res.json()
    assert norm_data["risk_score"] < 0.40
    assert norm_data["risk_level"] == "LOW"
    assert norm_data["inference_latency_ms"] < 100.0  # sub-100ms SLA accounting for CPU jitter

    # 2. High-risk anomalous transfer evaluation
    anomaly_res = client.post("/api/v1/risk/evaluate", json={
        "amount": 48000.00,
        "transaction_type": "CASH_OUT",
        "velocity_10m": 6,
        "device_switch": True
    }, headers=headers)
    assert anomaly_res.status_code == 200
    anom_data = anomaly_res.json()
    assert anom_data["risk_score"] >= 0.75
    assert anom_data["risk_level"] == "HIGH"
    assert anom_data["decision"] == "BLOCK_AND_FLAG"
    assert len(anom_data["reasons"]) > 0

def test_model_metrics_and_overview(client):
    adm_token = get_auth_token(client, "admin@example.com", "Admin@1234")
    headers = {"Authorization": f"Bearer {adm_token}"}

    # Check metrics
    m_res = client.get("/api/v1/risk/metrics", headers=headers)
    assert m_res.status_code == 200
    m_data = m_res.json()
    assert m_data["roc_auc"] >= 0.88
    assert m_data["training_samples"] >= 1000
    assert m_data["latency_p50_ms"] < 10.0

    # Check overview
    o_res = client.get("/api/v1/risk/overview", headers=headers)
    assert o_res.status_code == 200
    o_data = o_res.json()
    assert o_data["total_transactions"] >= 2
    assert "high_risk_transactions" in o_data

def test_master_freeze_state_machine_and_latency(client):
    c_token = get_auth_token(client, "customer@example.com")
    headers = {"Authorization": f"Bearer {c_token}"}

    # 1. Reject invalid PIN
    bad_pin = client.post("/api/v1/freeze/trigger", json={
        "freeze_pin": "9999",
        "reason": "Test bad pin"
    }, headers=headers)
    assert bad_pin.status_code == 401
    assert bad_pin.json()["error"]["code"] == "INVALID_FREEZE_PIN"

    # 2. Trigger freeze with correct PIN (1234)
    freeze_res = client.post("/api/v1/freeze/trigger", json={
        "freeze_pin": "1234",
        "reason": "Device stolen on bus"
    }, headers=headers)
    assert freeze_res.status_code == 200
    f_data = freeze_res.json()
    assert f_data["status"] == "FROZEN"
    assert f_data["is_frozen"] is True
    assert f_data["target_sla_met"] is True
    assert f_data["response_time_ms"] < 300.0  # Sub-300ms SLA!

    # 3. Assert old session token was revoked by Master Freeze!
    revoked_res = client.get("/api/v1/auth/me", headers=headers)
    assert revoked_res.status_code == 401
    assert revoked_res.json()["error"]["code"] == "SESSION_REVOKED"

    # 4. Re-authenticate to get read-only access for frozen account
    new_token = get_auth_token(client, "customer@example.com")
    new_headers = {"Authorization": f"Bearer {new_token}"}

    st_res = client.get("/api/v1/freeze/status", headers=new_headers)
    assert st_res.status_code == 200
    assert st_res.json()["is_frozen"] is True

    # 5. Outgoing transfer attempt must be blocked with HTTP 403 ACCOUNT_FROZEN
    tx_res = client.post("/api/v1/transactions/send", json={
        "receiver_identifier": "victim@example.com",
        "amount": 20.00
    }, headers=new_headers)
    assert tx_res.status_code == 403
    assert tx_res.json()["error"]["code"] == "ACCOUNT_FROZEN"

    # 6. Unfreeze with verified code
    unfreeze_res = client.post("/api/v1/freeze/unfreeze", json={
        "verification_code": "123456"
    }, headers=new_headers)
    assert unfreeze_res.status_code == 200
    assert unfreeze_res.json()["is_frozen"] is False
