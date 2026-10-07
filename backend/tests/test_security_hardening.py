"""
upay Pulse — Security Hardening & Audit Verification Tests (Workstream 11)
Validates:
1. Eradication of hardcoded unfreeze bypasses
2. Server-side RBAC enforcement
3. Mandatory Case Ticket ID & audit logging for administrative unfreeze
"""

import pytest
from backend.app.core.database import SessionLocal
from backend.app.models.user import User, UserStatus
from backend.app.models.audit import AuditLog

def get_auth_token(client, email, password=None):
    if password is None:
        password = "Admin@1234" if "admin" in email else "Demo@1234"
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_unauthorized_unfreeze_rejected(client):
    """Random codes must fail with 400 (no hardcoded bypass)."""
    token = get_auth_token(client, "victim@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/freeze/unfreeze", json={
        "verification_code": "999999"  # Fake code
    }, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_VERIFICATION_CODE"

def test_admin_secure_unfreeze_validation_and_audit(client):
    """Admin unfreeze requires Case Ticket ID, Reason, and produces AuditLog."""
    admin_token = get_auth_token(client, "admin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    cust_token = get_auth_token(client, "customer@example.com")
    cust_headers = {"Authorization": f"Bearer {cust_token}"}

    target_phone = "+8801700000001"

    # 1. Non-admin user cannot call admin secure unfreeze
    res_forbidden = client.post("/api/v1/freeze/admin-secure-unfreeze", json={
        "account_id": target_phone,
        "case_ticket_id": "CASE-2026-001",
        "reason": "Customer identity verified in person"
    }, headers=cust_headers)
    assert res_forbidden.status_code == 403

    # 2. Missing Case Ticket ID fails validation (422)
    res_missing_ticket = client.post("/api/v1/freeze/admin-secure-unfreeze", json={
        "account_id": target_phone,
        "case_ticket_id": "",
        "reason": "Customer identity verified in person"
    }, headers=admin_headers)
    assert res_missing_ticket.status_code == 422

    # 3. Missing Reason fails validation (422)
    res_missing_reason = client.post("/api/v1/freeze/admin-secure-unfreeze", json={
        "account_id": target_phone,
        "case_ticket_id": "CASE-2026-001",
        "reason": "Short"
    }, headers=admin_headers)
    assert res_missing_reason.status_code == 422

    # 4. Valid admin secure unfreeze succeeds and logs audit
    res_success = client.post("/api/v1/freeze/admin-secure-unfreeze", json={
        "account_id": target_phone,
        "case_ticket_id": "CASE-2026-8891",
        "reason": "Biometric verification confirmed at Savar Branch",
        "supervisor_mfa_token": "MFA-SUPERVISOR-AUTH"
    }, headers=admin_headers)
    assert res_success.status_code == 200
    data = res_success.json()
    assert data["case_ticket_id"] == "CASE-2026-8891"

    # Verify audit log in database
    db = SessionLocal()
    try:
        audit = db.query(AuditLog).filter(
            AuditLog.action == "SECURE_ADMIN_UNFREEZE"
        ).order_by(AuditLog.created_at.desc()).first()
        assert audit is not None
        assert "CASE-2026-8891" in audit.details
    finally:
        db.close()
