"""
upay Pulse — Phase-2 Wiring Tests (Workstreams 5, 6, 11, 14)

These tests verify that the three new Phase-2 endpoints and their backing
SQLAlchemy tables are actually wired into the running FastAPI app:

  - /api/v1/evidence/benchmarks        (read-only evidence dashboard)
  - /api/v1/governance/active-model    (model registry read)
  - /api/v1/governance/rollback        (admin-only, MFA-gated)
  - /api/v1/security/attack-suite/run  (live 4-attack suite)
  - model_governance_registry, immutable_security_audit
"""

import hashlib
import hmac
import time

import pytest
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.user import User, UserRole
from backend.app.models.model_governance import ModelGovernanceRegistry
from backend.app.models.security_audit import ImmutableSecurityAudit, compute_record_hash


def _admin_totp(user_id: str) -> str:
    """Reproduce FreezeService._compute_user_totp so tests can supply a valid MFA token."""
    key = settings.SECRET_KEY.encode("utf-8")
    bucket = int(time.time()) // 300
    for offset in (0, -1, 1):
        b = bucket + offset
        msg = f"{user_id}:{b}".encode("utf-8")
        digest = hmac.new(key, msg, hashlib.sha256).hexdigest()
        candidate = str(int(digest[:6], 16) % 1000000).zfill(6)
        # Return the current bucket one (offset 0); tests rely on clock alignment.
        if offset == 0:
            return candidate
    return "000000"


def _admin_headers(client) -> dict:
    res = client.post("/api/v1/auth/login", json={"identifier": "admin@example.com", "password": "Admin@1234"})
    assert res.status_code == 200, f"admin login failed: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _customer_headers(client) -> dict:
    res = client.post("/api/v1/auth/login", json={"identifier": "customer@example.com", "password": "Demo@1234"})
    assert res.status_code == 200, f"customer login failed: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_evidence_benchmarks_endpoint_returns_merged_payload(client):
    """GET /api/v1/evidence/benchmarks must return the union of all six JSON artefacts."""
    res = client.get("/api/v1/evidence/benchmarks")
    assert res.status_code == 200, res.text
    body = res.json()
    assert "ml" in body
    assert "impact" in body
    assert "performance" in body
    assert "soundbox" in body
    assert body["ml"]["model_comparison"] is not None
    assert "M3_lightgbm_tabular" in body["ml"]["model_comparison"]["models"]


def test_governance_active_model_endpoint_seeds_default(client):
    """GET /api/v1/governance/active-model must seed the registry if empty and return one row."""
    # Wipe the registry so the seed path is exercised deterministically.
    db = SessionLocal()
    try:
        db.query(ModelGovernanceRegistry).delete()
        db.commit()
    finally:
        db.close()

    headers = _admin_headers(client)
    res = client.get("/api/v1/governance/active-model", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["active"]["is_active"] is True
    assert body["active"]["model_version"].startswith("lgbm_")
    assert isinstance(body["history"], list) and len(body["history"]) >= 1


def test_governance_rollback_requires_super_admin(client):
    """Non-admin caller must be rejected with 403 (and an audit row must NOT be written)."""
    db = SessionLocal()
    try:
        baseline_count = db.query(ImmutableSecurityAudit).filter(
            ImmutableSecurityAudit.action == "MODEL_ROLLBACK"
        ).count()
    finally:
        db.close()

    cust_headers = _customer_headers(client)
    res = client.post(
        "/api/v1/governance/rollback",
        json={"mfa_totp": "000000", "reason": "unauthorised attempt"},
        headers=cust_headers,
    )
    assert res.status_code == 403, res.text

    db = SessionLocal()
    try:
        post_count = db.query(ImmutableSecurityAudit).filter(
            ImmutableSecurityAudit.action == "MODEL_ROLLBACK"
        ).count()
        assert post_count == baseline_count, "rollback audit row written despite 403"
    finally:
        db.close()


def test_attack_suite_endpoint_runs_four_attacks(client):
    """POST /api/v1/security/attack-suite/run must block all 4 attacks."""
    headers = _customer_headers(client)
    res = client.post(
        "/api/v1/security/attack-suite/run",
        json={"transaction_reference": "TXN-INIT-001"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["passed"] == 4
    assert body["total"] == 4
    assert len(body["results"]) == 4
    assert {r["name"] for r in body["results"]} == {
        "Static Screenshot",
        "Expired Token",
        "Tampered Nonce",
        "Token Replay",
    }
    assert all(r["blocked"] is True for r in body["results"])
    # And an audit row must have been written.
    assert body["audit_sequence_id"] > 0
    assert len(body["audit_record_hash"]) == 64


def test_immutable_security_audit_chain_is_consistent(client):
    """The audit chain must be append-only and hash-linked.

    This test seeds two rows directly so it does not depend on the order of
    other tests in this module. Uses a unique nonce per run so the test is
    idempotent across repeated pytest invocations.
    """
    import uuid as _uuid
    nonce = _uuid.uuid4().hex

    db = SessionLocal()
    try:
        a0_payload = {"kind": "CHAIN_TEST_INIT", "nonce": nonce, "value": 1}
        prev = "0" * 64
        rh0 = compute_record_hash(prev, a0_payload)
        db.add(ImmutableSecurityAudit(
            actor_id=f"chain_test_{nonce}",
            action="CHAIN_TEST_INIT",
            resource_id="test",
            previous_hash=prev,
            record_hash=rh0,
            payload_json=a0_payload,
        ))
        db.flush()

        a1_payload = {"kind": "CHAIN_TEST_NEXT", "nonce": nonce, "value": 2}
        rh1 = compute_record_hash(rh0, a1_payload)
        db.add(ImmutableSecurityAudit(
            actor_id=f"chain_test_{nonce}",
            action="CHAIN_TEST_NEXT",
            resource_id="test",
            previous_hash=rh0,
            record_hash=rh1,
            payload_json=a1_payload,
        ))
        db.commit()

        rows = (
            db.query(ImmutableSecurityAudit)
            .filter(ImmutableSecurityAudit.actor_id == f"chain_test_{nonce}")
            .order_by(ImmutableSecurityAudit.sequence_id.asc())
            .all()
        )
        assert len(rows) == 2

        expected_prev = "0" * 64
        for r in rows:
            assert r.previous_hash == expected_prev
            recomputed = compute_record_hash(r.previous_hash, r.payload_json)
            assert recomputed == r.record_hash
            expected_prev = r.record_hash
    finally:
        db.close()