import pytest
import uuid
from backend.app.core.database import SessionLocal
from backend.app.models.user import User

def get_auth_token(client, email, password="Demo@1234"):
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_send_money_and_idempotency(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}
    
    # 1. Successful transfer of 50 BDT from customer to victim
    idemp_key = f"IDEMP-{uuid.uuid4().hex[:8]}"
    send_payload = {
        "receiver_identifier": "victim@example.com",
        "amount": 50.00,
        "category": "PeerTransfer",
        "description": "Lunch split",
        "idempotency_key": idemp_key
    }

    res1 = client.post("/api/v1/transactions/send", json=send_payload, headers=c_headers)
    assert res1.status_code == 201
    txn1 = res1.json()
    assert txn1["amount"] == 50.00
    assert txn1["status"] == "COMPLETED"

    # 2. Idempotency replay with same key must return same reference without double-deduction
    res2 = client.post("/api/v1/transactions/send", json=send_payload, headers=c_headers)
    assert res2.status_code == 201
    txn2 = res2.json()
    assert txn2["id"] == txn1["id"]
    assert txn2["transaction_reference"] == txn1["transaction_reference"]

def test_grace_overdraft_shortfall_and_approval(client):
    # Customer balance was initially 500, sent 50 -> balance is now ~450
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    # Get current balance
    me_res = client.get("/api/v1/auth/me", headers=c_headers)
    current_bal = me_res.json()["profile"]["wallet_balance"]

    # 1. Attempt transfer with shortfall of 20 BDT without applying grace
    transfer_amount = current_bal + 20.0
    fail_res = client.post("/api/v1/transactions/send", json={
        "receiver_identifier": "victim@example.com",
        "amount": transfer_amount,
        "apply_grace_if_needed": False
    }, headers=c_headers)
    
    assert fail_res.status_code == 400
    fail_data = fail_res.json()
    assert fail_data["error"]["code"] == "INSUFFICIENT_FUNDS_GRACE_OFFERED"
    assert fail_data["error"]["details"]["grace_eligible"] is True
    assert fail_data["error"]["details"]["shortfall"] == 20.0

    # 2. Re-attempt with apply_grace_if_needed = True -> Approved!
    success_res = client.post("/api/v1/transactions/send", json={
        "receiver_identifier": "victim@example.com",
        "amount": transfer_amount,
        "apply_grace_if_needed": True
    }, headers=c_headers)

    assert success_res.status_code == 201
    succ_data = success_res.json()
    assert succ_data["status"] == "COMPLETED"
    assert succ_data["applied_grace_amount"] == 20.0

    # Verify updated customer profile: wallet = 0, grace_balance = 20
    me_after = client.get("/api/v1/auth/me", headers=c_headers)
    assert me_after.json()["profile"]["wallet_balance"] == 0.00
    assert me_after.json()["profile"]["grace_balance"] == 20.00

def test_agent_cash_in_auto_recovers_grace(client):
    # Agent logs in
    a_token = get_auth_token(client, "agent@example.com")
    a_headers = {"Authorization": f"Bearer {a_token}"}

    # Customer currently has 20.00 grace_balance and 0.00 wallet_balance
    # Agent performs Cash-In of 100.00 BDT
    cash_in_res = client.post("/api/v1/transactions/cash-in", json={
        "customer_phone": "+8801700000001",
        "amount": 100.00
    }, headers=a_headers)

    assert cash_in_res.status_code == 201
    assert cash_in_res.json()["status"] == "COMPLETED"

    # Customer profile should now have grace_balance = 0, and wallet_balance = 80.00 (100 - 20)
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}
    me_res = client.get("/api/v1/auth/me", headers=c_headers)
    assert me_res.json()["profile"]["grace_balance"] == 0.00
    assert me_res.json()["profile"]["wallet_balance"] == 80.00

def test_frozen_sender_is_blocked(client):
    # Freeze victim account in db directly for test
    db = SessionLocal()
    victim = db.query(User).filter(User.email == "victim@example.com").first()
    victim.is_frozen = True
    db.commit()
    db.close()

    v_token = get_auth_token(client, "victim@example.com")
    v_headers = {"Authorization": f"Bearer {v_token}"}

    res = client.post("/api/v1/transactions/send", json={
        "receiver_identifier": "customer@example.com",
        "amount": 100.00
    }, headers=v_headers)

    assert res.status_code == 403
    assert res.json()["error"]["code"] == "ACCOUNT_FROZEN"

    # Clean up unfreeze
    db = SessionLocal()
    victim = db.query(User).filter(User.email == "victim@example.com").first()
    victim.is_frozen = False
    db.commit()
    db.close()

def test_transaction_history_role_isolation(client):
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    hist_res = client.get("/api/v1/transactions/history", headers=c_headers)
    assert hist_res.status_code == 200
    items = hist_res.json()["items"]
    assert len(items) > 0
    # Customer only sees their transactions
    for item in items:
        assert "customer@example.com" in [item["sender_name"], item["receiver_name"]] or item["sender_phone"] == "+8801700000001" or item["receiver_phone"] == "+8801700000001"
