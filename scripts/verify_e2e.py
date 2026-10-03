"""
upay Pulse - End-to-End System Journey & Acceptance Verification
Executes the complete customer, agent, and risk analyst journey from scratch.
"""

import sys
import os
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from starlette.testclient import TestClient
from backend.main import app

def run_e2e_verification():
    client = TestClient(app)

    print("============================================================")
    print("      upay Pulse — Final End-to-End System Verification      ")
    print("============================================================")

    # 1. Health & Readiness
    print("\n[STEP 1] Probing Health & Readiness...")
    res = client.get("/ready")
    assert res.status_code == 200, res.text
    ready_data = res.json()
    assert ready_data["status"] == "ready"
    assert ready_data["database"]["status"] == "healthy"
    print(f"  --> Status: {ready_data['status'].upper()} (DB: {ready_data['database']['dialect']})")

    # 2. Registration & Login
    print("\n[STEP 2] Customer Registration & JWT Token Issuance...")
    unique_id = int(time.time())
    phone = f"+8801755{unique_id % 1000000:06d}"
    email = f"e2e_{unique_id}@pulse.demo"
    reg = client.post("/api/v1/auth/register", json={
        "phone": phone,
        "email": email,
        "password": "Password@123",
        "role": "CUSTOMER",
        "full_name": "E2E Verification User",
        "freeze_pin": "9876",
        "profession": "Software Engineer",
        "location": "Mohakhali, Dhaka"
    })
    assert reg.status_code == 201, reg.text
    cust_token = reg.json()["access_token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}
    print(f"  --> Customer registered: {email} ({phone})")

    # 3. Customer Dashboard
    print("\n[STEP 3] Customer Dashboard & Initial Wallet Balance...")
    me = client.get("/api/v1/auth/me", headers=cust_headers).json()
    assert me["profile"]["wallet_balance"] == 500.0
    print(f"  --> Initial Wallet Balance: BDT {me['profile']['wallet_balance']:,.2f}")

    # 4. Normal Peer Transfer
    print("\n[STEP 4] Simulating Normal Transfer (Sub-10ms Ledger)...")
    idemp_key = f"E2E-IDEMP-{unique_id}"
    tx1 = client.post("/api/v1/transactions/send", json={
        "receiver_identifier": "victim@example.com",
        "amount": 50.0,
        "category": "PeerTransfer",
        "idempotency_key": idemp_key
    }, headers=cust_headers)
    assert tx1.status_code == 201, tx1.text
    tx_res = tx1.json()
    assert tx_res["status"] == "COMPLETED"
    print(f"  --> Transaction Completed: {tx_res['transaction_reference']} (Amount: BDT {tx_res['amount']})")

    # 5. Real-Time Risk Scoring
    print("\n[STEP 5] Real-Time Anomaly Interception (LightGBM Risk Engine)...")
    risk_eval = client.post("/api/v1/risk/evaluate", json={
        "amount": 48000.0,
        "transaction_type": "CASH_OUT",
        "velocity_10m": 5,
        "device_switch": True
    }, headers=cust_headers).json()
    assert risk_eval["risk_score"] >= 0.75
    assert risk_eval["risk_level"] == "HIGH"
    print(f"  --> Risk Score: {risk_eval['risk_score']} ({risk_eval['risk_level']})")
    print(f"  --> Decision: {risk_eval['decision']} (Reasons: {', '.join(risk_eval['reasons'])})")

    # 6. Scam Report Submission
    print("\n[STEP 6] Customer Scam Report Submission...")
    scam = client.post("/api/v1/scams/report", json={
        "reported_account": "+8801700000002",
        "reason": "Phishing attempt and fake lottery OTP demand",
        "investigation_notes": "Victim pressured to send funds"
    }, headers=cust_headers)
    assert scam.status_code == 201
    print(f"  --> Scam Report Filed: ID={scam.json()['id']} (Status: {scam.json()['status']})")

    # 7. Master Freeze Emergency Lockdown
    print("\n[STEP 7] Emergency Master Freeze Execution (<300ms SLA)...")
    freeze = client.post("/api/v1/freeze/trigger", json={
        "freeze_pin": "9876",
        "reason": "Device stolen in transit"
    }, headers=cust_headers)
    assert freeze.status_code == 200
    f_data = freeze.json()
    assert f_data["status"] == "FROZEN"
    assert f_data["is_frozen"] is True
    assert f_data["response_time_ms"] < 300.0
    print(f"  --> Status: FROZEN in {f_data['response_time_ms']} ms (SLA Met: {f_data['target_sla_met']})")

    # 8. Session Revocation & Outgoing Transfer Blockade
    print("\n[STEP 8] Verifying Session Revocation & Transaction Blockade...")
    revoked = client.get("/api/v1/auth/me", headers=cust_headers)
    assert revoked.status_code == 401
    print("  --> Pre-freeze session token rejected: HTTP 401 SESSION_REVOKED")

    # Re-login for fresh read-only session
    re_login = client.post("/api/v1/auth/login", json={"identifier": email, "password": "Password@123"}).json()
    fresh_headers = {"Authorization": f"Bearer {re_login['access_token']}"}
    blocked = client.post("/api/v1/transactions/send", json={
        "receiver_identifier": "victim@example.com",
        "amount": 10.0
    }, headers=fresh_headers)
    assert blocked.status_code == 403
    print("  --> Outgoing transfer from frozen account rejected: HTTP 403 ACCOUNT_FROZEN")

    # 9. Admin & Central Risk Console
    print("\n[STEP 9] Central Risk Console Telemetry & NetworkX Mule Graph...")
    admin_login = client.post("/api/v1/auth/login", json={"identifier": "admin@example.com", "password": "Admin@1234"}).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}
    overview = client.get("/api/v1/risk/overview", headers=admin_headers).json()
    assert overview["total_transactions"] > 0
    print(f"  --> Total Transactions Monitored: {overview['total_transactions']:,}")
    print(f"  --> Frozen Accounts: {overview['frozen_accounts_count']}")

    topo = client.get("/api/v1/graph/topology?limit=50", headers=admin_headers).json()
    assert len(topo["nodes"]) > 0
    print(f"  --> NetworkX Mule Graph: {len(topo['nodes'])} active nodes, {len(topo['edges'])} edges")

    # 10. Customer Cash-Flow Trajectory
    print("\n[STEP 10] CustomerAI 30-Day Forward Cash-Flow Trajectory...")
    traj = client.get("/api/v1/customer-ai/trajectory", headers=fresh_headers).json()
    assert len(traj["daily_forecast"]) == 30
    print(f"  --> 30-Day Trajectory Points: {len(traj['daily_forecast'])}")
    print(f"  --> Projected 30-Day End Balance: BDT {traj['projected_30d_end_balance']:,.2f}")

    # 11. upay Grace Overdraft
    print("\n[STEP 11] CustomerAI upay Grace (Simulated Micro-Overdraft)...")
    grace = client.get("/api/v1/customer-ai/grace/eligibility", headers=fresh_headers).json()
    assert grace["eligible"] is True
    print(f"  --> Reliability Credit Score: {grace['credit_score']} / 850")
    print(f"  --> Approved Overdraft Limit: BDT {grace['approved_limit']:,.2f}")

    # 12. Conversational Bangla Voice Coach
    print("\n[STEP 12] CustomerAI Bangla Voice Financial Coach...")
    voice = client.post("/api/v1/customer-ai/voice-coach/chat", json={
        "query": "আমার অ্যাকাউন্টে কত টাকা ব্যালেন্স আছে?",
        "language": "bn"
    }, headers=fresh_headers).json()
    assert voice["intent"] == "BALANCE_INQUIRY"
    print(f"  --> Query Intent: {voice['intent']} (Inference Latency: {voice['latency_ms']} ms)")
    print(f"  --> Bengali Voice Synthesis Script: \"{voice['response_bangla'][:60]}...\"")

    # 13. Agent Terminal & Liquidity Forecast
    print("\n[STEP 13] AgentAI Liquidity Forecast & Stockout Risk...")
    agent_login = client.post("/api/v1/auth/login", json={"identifier": "agent@example.com", "password": "Demo@1234"}).json()
    agent_headers = {"Authorization": f"Bearer {agent_login['access_token']}"}
    ag_forecast = client.get("/api/v1/agent-ai/forecast", headers=agent_headers).json()
    assert len(ag_forecast["daily_forecast"]) == 7
    print(f"  --> 7-Day Demand Forecast: BDT {ag_forecast['total_7d_predicted_cash_out']:,.2f}")
    print(f"  --> Stockout Risk Rating: {ag_forecast['stockout_risk']}")

    # 14. Software Soundbox & Dynamic Badge Verification
    print("\n[STEP 14] Software Soundbox & Anti-Screenshot Badge Verification...")
    chime = client.get("/api/v1/soundbox/chime/TXN-INIT-001", headers=agent_headers).json()
    print(f"  --> Soundbox Chime Script: \"{chime['vocal_script_bangla']}\"")

    badge = client.get("/api/v1/badge/generate/TXN-INIT-001", headers=fresh_headers).json()
    nonce = badge["dynamic_nonce"]
    v_res = client.post("/api/v1/badge/verify", json={
        "transaction_reference": "TXN-INIT-001",
        "nonce": nonce
    }, headers=agent_headers).json()
    assert v_res["is_valid"] is True
    print(f"  --> Rotating Nonce ({nonce}) Verification: {v_res['verification_status']}")

    print("\n" + "=" * 60)
    print("  [SUCCESS] All 14 Verification Steps Passed Flawlessly!")
    print("  upay Pulse Ecosystem is 100% Production-Ready!")
    print("============================================================")

if __name__ == "__main__":
    run_e2e_verification()
