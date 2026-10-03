import pytest
from backend.app.core.database import SessionLocal
from backend.app.models.user import User

def get_auth_token(client, email, password=None):
    if password is None:
        password = "Admin@1234" if "admin" in email else "Demo@1234"
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_soundbox_chime_generation(client):
    a_token = get_auth_token(client, "agent@example.com")
    a_headers = {"Authorization": f"Bearer {a_token}"}

    res = client.get("/api/v1/soundbox/chime/TXN-INIT-001", headers=a_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["transaction_reference"] == "TXN-INIT-001"
    assert data["amount"] == 500.00
    assert data["amount_bangla"] == "৫০০"
    assert "উপায় সফল!" in data["vocal_script_bangla"]
    assert "৫০০ টাকা জমা হয়েছে।" in data["vocal_script_bangla"]
    assert len(data["chime_tone_frequency_hz"]) == 3
    assert data["soundbox_status"] == "BROADCAST_READY"

def test_dynamic_anti_screenshot_badge_flow(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    # 1. Generate live dynamic badge
    gen_res = client.get("/api/v1/badge/generate/TXN-INIT-001", headers=c_headers)
    assert gen_res.status_code == 200
    badge = gen_res.json()

    assert badge["transaction_reference"] == "TXN-INIT-001"
    assert badge["status"] == "COMPLETED"
    assert len(badge["dynamic_nonce"]) == 6
    assert 1 <= badge["seconds_remaining_in_window"] <= 60
    assert "pulse_color" in badge
    assert badge["pulse_frequency_hz"] > 0

    valid_nonce = badge["dynamic_nonce"]

    # 2. Merchant verifies the authentic badge
    a_token = get_auth_token(client, "agent@example.com")
    a_headers = {"Authorization": f"Bearer {a_token}"}

    verify_res = client.post("/api/v1/badge/verify", json={
        "transaction_reference": "TXN-INIT-001",
        "nonce": valid_nonce
    }, headers=a_headers)

    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["is_valid"] is True
    assert v_data["verification_status"] == "AUTHENTIC_LIVE"
    assert v_data["amount"] == 500.00

    # 3. Fraudster shows a fake/expired nonce (static screenshot)
    counterfeit_res = client.post("/api/v1/badge/verify", json={
        "transaction_reference": "TXN-INIT-001",
        "nonce": "INVALID"
    }, headers=a_headers)

    assert counterfeit_res.status_code == 200
    c_data = counterfeit_res.json()
    assert c_data["is_valid"] is False
    assert c_data["verification_status"] == "EXPIRED_OR_COUNTERFEIT"
    assert "FRAUD WARNING" in c_data["message"]

    # 4. Fabricated reference that does not exist
    not_found_res = client.post("/api/v1/badge/verify", json={
        "transaction_reference": "NON-EXISTENT-REF",
        "nonce": "123456"
    }, headers=a_headers)

    assert not_found_res.status_code == 200
    nf_data = not_found_res.json()
    assert nf_data["is_valid"] is False
    assert nf_data["verification_status"] == "NOT_FOUND"
