"""
upay Pulse — Phase-2 Security endpoint: dynamic-nonce attack suite (Workstream 7.3)

POST /api/v1/security/attack-suite/run
    Executes the 4 canonical anti-screenshot attack scenarios against the real
    BadgeService and returns the verdict. The same helper is invoked by the
    pytest suite, so a passing live API and a passing test cannot diverge.

The endpoint also appends an immutable_security_audit record so the audit chain
records every live invocation.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.security_audit import ImmutableSecurityAudit, compute_record_hash
from backend.app.services.badge_service import BadgeService


router = APIRouter()


class AttackSuiteRequest(BaseModel):
    transaction_reference: str = "TXN-INIT-001"


def _last_chain_hash(db: Session) -> str:
    last = (
        db.query(ImmutableSecurityAudit)
        .order_by(ImmutableSecurityAudit.sequence_id.desc())
        .first()
    )
    if last is None:
        return "0" * 64
    return last.record_hash


@router.post("/attack-suite/run", tags=["Security: Anti-Screenshot Attack Suite"])
def run_attack_suite(
    req: AttackSuiteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Live execution of the 4 cryptographic attack vectors against BadgeService.
    Returns a per-attack verdict and the overall pass count.
    """
    try:
        report = BadgeService.run_attack_suite(db, req.transaction_reference)
    finally:
        # Always clear the in-memory consumed-nonce cache so the run is repeatable.
        BadgeService._consumed_nonces.clear()

    # Append an immutable audit record summarising the run.
    prev = _last_chain_hash(db)
    payload = {
        "kind": "ATTACK_SUITE_RUN",
        "transaction_reference": req.transaction_reference,
        "passed": report["passed"],
        "total": report["total"],
        "actor_id": current_user.id,
        "actor_role": current_user.role.value if current_user.role else "UNKNOWN",
    }
    audit = ImmutableSecurityAudit(
        actor_id=current_user.id,
        action="ATTACK_SUITE_RUN",
        resource_id=req.transaction_reference,
        previous_hash=prev,
        record_hash=compute_record_hash(prev, payload),
        payload_json=payload,
    )
    db.add(audit)
    db.commit()

    return {
        **report,
        "audit_record_hash": audit.record_hash,
        "audit_sequence_id": audit.sequence_id,
    }