"""
upay Pulse — Citizen False-Positive Dispute & Human-in-the-Loop Triage Tests (Workstream 12)
Validates:
1. Citizen submission of false-positive dispute / emergency appeals
2. Role-based security (citizens cannot triage appeals)
3. Risk analyst review, human unfreeze action, and mandatory audit log generation
4. Idempotency (resolved appeals cannot be re-triaged)
"""

import pytest
from backend.app.core.database import SessionLocal
from backend.app.models.user import User, UserStatus
from backend.app.models.appeal import Appeal, AppealStatus, AppealReviewAction
from backend.app.models.audit import AuditLog
from backend.app.models.freeze import FreezeAction, FreezeActionType

def get_auth_token(client, email, password=None):
    if password is None:
        password = "Admin@1234" if "admin" in email else "Demo@1234"
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_citizen_appeal_and_analyst_triage_flow(client):
    db = SessionLocal()
    try:
        cust_token = get_auth_token(client, "victim@example.com")
        cust_headers = {"Authorization": f"Bearer {cust_token}"}

        admin_token = get_auth_token(client, "admin@example.com")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Setup victim user as frozen to test recovery
        victim = db.query(User).filter(User.email == "victim@example.com").first()
        assert victim is not None
        victim.is_frozen = True
        victim.status = UserStatus.FROZEN
        db.commit()

        # 1. Citizen submits false-positive appeal
        appeal_payload = {
            "category": "EMERGENCY_MEDICAL",
            "explanation": "Urgent transfer for hospital emergency at Dhaka Medical College Hospital.",
            "transaction_reference": "TXN-EMERG-999",
            "supporting_document_ref": "DOC-DMCH-RECEIPT-4029"
        }
        res_submit = client.post("/api/v1/appeals/submit", json=appeal_payload, headers=cust_headers)
        assert res_submit.status_code == 201
        appeal_data = res_submit.json()
        appeal_id = appeal_data["id"]
        assert appeal_data["status"] == "PENDING"
        assert appeal_data["category"] == "EMERGENCY_MEDICAL"
        assert appeal_data["user_email"] == "victim@example.com"

        # 2. Citizen checks their appeals list
        res_my = client.get("/api/v1/appeals/my", headers=cust_headers)
        assert res_my.status_code == 200
        my_appeals = res_my.json()
        assert my_appeals["total"] >= 1
        assert any(a["id"] == appeal_id for a in my_appeals["items"])

        # 3. Citizen cannot review their own appeal (403 Forbidden)
        res_unauthorized_review = client.post(
            f"/api/v1/appeals/{appeal_id}/review",
            json={
                "action": "UNFREEZE_ACCOUNT",
                "review_notes": "Attempting self unfreeze"
            },
            headers=cust_headers
        )
        assert res_unauthorized_review.status_code == 403

        # 4. Risk Analyst lists pending appeals in Risk Console
        res_admin_list = client.get("/api/v1/appeals?status=PENDING", headers=admin_headers)
        assert res_admin_list.status_code == 200
        pending_list = res_admin_list.json()
        assert any(a["id"] == appeal_id for a in pending_list["items"])

        # 5. Risk Analyst reviews and approves appeal, unfreezing user
        review_payload = {
            "action": "UNFREEZE_ACCOUNT",
            "review_notes": "Hospital admission documents verified with DMCH reception desk."
        }
        res_review = client.post(
            f"/api/v1/appeals/{appeal_id}/review",
            json=review_payload,
            headers=admin_headers
        )
        assert res_review.status_code == 200
        resolved_data = res_review.json()
        assert resolved_data["status"] == "APPROVED"
        assert resolved_data["review_action"] == "UNFREEZE_ACCOUNT"
        assert resolved_data["reviewer_email"] == "admin@example.com"
        assert resolved_data["resolved_at"] is not None

        # 6. Verify user unfreeze in database
        db.refresh(victim)
        assert victim.is_frozen is False
        assert victim.status == UserStatus.ACTIVE

        # 7. Verify freeze action and audit log created
        freeze_action = db.query(FreezeAction).filter(
            FreezeAction.user_id == victim.id,
            FreezeAction.action_type == FreezeActionType.UNFREEZE_VERIFIED
        ).first()
        assert freeze_action is not None

        audit = db.query(AuditLog).filter(
            AuditLog.resource == "APPEAL",
            AuditLog.resource_id == appeal_id
        ).first()
        assert audit is not None
        assert audit.action == "APPEAL_REVIEWED"

        # 8. Attempting to review an already-resolved appeal must fail with 400
        res_duplicate = client.post(
            f"/api/v1/appeals/{appeal_id}/review",
            json=review_payload,
            headers=admin_headers
        )
        assert res_duplicate.status_code == 400
        assert res_duplicate.json()["error"]["code"] == "ALREADY_RESOLVED"

    finally:
        db.close()
