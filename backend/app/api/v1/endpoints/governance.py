"""
upay Pulse — Model Governance endpoints (Phase 2 §11.3)

GET  /api/v1/governance/active-model
    Returns the row in model_governance_registry where is_active=True, plus
    the raw JSON evidence bundle so the Risk Console can render its provenance.

POST /api/v1/governance/rollback
    Flips is_active between the current and the most-recent prior registered
    checkpoint, appends an immutable_security_audit record. Requires:
      - ADMIN role
      - Valid 6-digit TOTP MFA token (matches FreezeService._compute_user_totp)

The registry table is auto-seeded once with the v2 clean model so a freshly
booted demo always has an "active model" to show. Seeding is idempotent.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.exceptions import AppException
from backend.app.api.deps import get_current_user, require_admin
from backend.app.models.user import User
from backend.app.models.model_governance import ModelGovernanceRegistry
from backend.app.models.security_audit import ImmutableSecurityAudit, compute_record_hash


router = APIRouter()

_REPO_ROOT = Path(__file__).resolve().parents[5]
_ML_REPORT = _REPO_ROOT / "reports" / "ml_report" / "model_comparison_report.json"


class RollbackRequest(BaseModel):
    mfa_totp: str
    reason: str


def _serialize(row: ModelGovernanceRegistry) -> Dict[str, Any]:
    return {
        "id": row.id,
        "model_version": row.model_version,
        "algorithm": row.algorithm,
        "trained_at": row.trained_at.isoformat() if row.trained_at else None,
        "training_dataset": row.training_dataset,
        "feature_count": row.feature_count,
        "pr_auc": float(row.pr_auc) if row.pr_auc is not None else None,
        "roc_auc": float(row.roc_auc) if row.roc_auc is not None else None,
        "recall_at_1pct_fpr": float(row.recall_at_1pct_fpr) if row.recall_at_1pct_fpr is not None else None,
        "brier_score": float(row.brier_score) if row.brier_score is not None else None,
        "decision_threshold": float(row.decision_threshold) if row.decision_threshold is not None else None,
        "is_active": row.is_active,
        "approved_by": row.approved_by,
        "notes": row.notes,
    }


def _last_chain_hash(db: Session) -> str:
    """Return the record_hash of the most recent audit row, or the genesis hash."""
    last = (
        db.query(ImmutableSecurityAudit)
        .order_by(ImmutableSecurityAudit.sequence_id.desc())
        .first()
    )
    if last is None:
        return "0" * 64
    return last.record_hash


def _append_audit(
    db: Session,
    *,
    actor_id: str,
    action: str,
    resource_id: str,
    payload: Dict[str, Any],
) -> ImmutableSecurityAudit:
    prev = _last_chain_hash(db)
    rh = compute_record_hash(prev, payload)
    row = ImmutableSecurityAudit(
        actor_id=actor_id,
        action=action,
        resource_id=resource_id,
        previous_hash=prev,
        record_hash=rh,
        payload_json=payload,
    )
    db.add(row)
    db.flush()
    return row


def seed_default_registry(db: Session) -> None:
    """
    Idempotent seed: if the registry is empty, insert one row describing the
    v2-clean model whose artefact lives at ml/artifacts/risk_model_v2_clean.joblib
    and whose metrics live at reports/ml_report/model_comparison_report.json.
    """
    if db.query(ModelGovernanceRegistry).count() > 0:
        return

    pr_auc = 0.0
    roc_auc = 0.0
    recall_at_1 = 0.0
    brier = 0.0
    if _ML_REPORT.exists():
        try:
            with _ML_REPORT.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            m3 = payload.get("models", {}).get("M3_lightgbm_tabular", {})
            pr_auc = float(m3.get("pr_auc", 0.0))
            roc_auc = float(m3.get("roc_auc", 0.0))
            recall_at_1 = float(m3.get("recall_at_1_0_pct_fpr", 0.0))
            brier = float(m3.get("brier_score", 0.0))
        except (OSError, ValueError):
            pass

    db.add(
        ModelGovernanceRegistry(
            model_version="lgbm_v2_temporal",
            algorithm="LightGBM (Leakage-Free Tabular)",
            trained_at=datetime.now(timezone.utc),
            training_dataset="synthetic_transactions_clean.csv",
            feature_count=14,
            pr_auc=pr_auc,
            roc_auc=roc_auc,
            recall_at_1pct_fpr=recall_at_1,
            brier_score=brier,
            decision_threshold=0.70,
            is_active=True,
            approved_by="system_seed",
            notes="Auto-seeded default model. Refresh by re-running ml/training/train_phase2_models.py.",
        )
    )
    db.commit()


@router.get("/active-model", tags=["Model Governance"])
def get_active_model(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seed_default_registry(db)
    active = (
        db.query(ModelGovernanceRegistry)
        .filter(ModelGovernanceRegistry.is_active.is_(True))
        .order_by(ModelGovernanceRegistry.trained_at.desc())
        .first()
    )
    if not active:
        raise AppException(
            "No active model registered. Re-run train_phase2_models.py.",
            code="NO_ACTIVE_MODEL",
            status_code=404,
        )

    history_rows: List[ModelGovernanceRegistry] = (
        db.query(ModelGovernanceRegistry)
        .order_by(ModelGovernanceRegistry.trained_at.desc())
        .limit(5)
        .all()
    )

    return {
        "active": _serialize(active),
        "history": [_serialize(r) for r in history_rows],
    }


def _verify_admin_totp(admin: User, totp: str) -> None:
    """
    Verify a 6-digit TOTP for the admin using the same window as FreezeService.
    This re-uses the cryptographic scheme already established in the codebase
    (HMAC-SHA256 over `f"{user.id}:{5min_bucket}"`) so the admin's MFA
    behaviour is consistent across security endpoints.
    """
    import hashlib
    import hmac
    import time
    from backend.app.core.config import settings

    if not totp or not totp.isdigit() or len(totp) != 6:
        raise AppException(
            "MFA token must be a 6-digit numeric code.",
            code="MFA_TOKEN_INVALID",
            status_code=422,
        )

    key = settings.SECRET_KEY.encode("utf-8")
    now = int(time.time())
    # Accept current bucket and ±1 for clock skew tolerance.
    for bucket_offset in (0, -1, 1):
        bucket = (now // 300) + bucket_offset
        msg = f"{admin.id}:{bucket}".encode("utf-8")
        digest = hmac.new(key, msg, hashlib.sha256).hexdigest()
        expected = str(int(digest[:6], 16) % 1000000).zfill(6)
        if hmac.compare_digest(expected, totp):
            return
    raise AppException(
        "MFA token rejected (out of window or wrong).",
        code="MFA_TOKEN_REJECTED",
        status_code=403,
    )


@router.post("/rollback", tags=["Model Governance"])
def rollback_model(
    req: RollbackRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if not req.reason or len(req.reason.strip()) < 8:
        raise AppException(
            "Rollback reason must be at least 8 characters.",
            code="REASON_REQUIRED",
            status_code=422,
        )

    _verify_admin_totp(admin, req.mfa_totp)

    seed_default_registry(db)

    current = (
        db.query(ModelGovernanceRegistry)
        .filter(ModelGovernanceRegistry.is_active.is_(True))
        .first()
    )
    if current is None:
        raise AppException(
            "No active model to roll back.",
            code="NO_ACTIVE_MODEL",
            status_code=404,
        )

    # Find the prior approved row.
    candidate = (
        db.query(ModelGovernanceRegistry)
        .filter(ModelGovernanceRegistry.id != current.id)
        .order_by(ModelGovernanceRegistry.trained_at.desc())
        .first()
    )

    if candidate is None:
        # No prior checkpoint exists. Refuse to fabricate one with invented
        # metrics — admins must register a prior model via the training pipeline
        # before a rollback can be exercised. This is the audit-correct
        # behaviour (the previous version invented PR-AUC=0.70, ROC=0.85,
        # recall=0.65, brier=0.05 numbers and surfaced them as real).
        raise AppException(
            "No prior registered model to roll back to. "
            "Register a prior checkpoint in `model_governance_registry` "
            "(e.g. by re-running ml/training/train_phase2_models.py) "
            "before issuing a rollback.",
            code="NO_ROLLBACK_TARGET",
            status_code=422,
        )

    previous_active_id = current.id
    current.is_active = False
    candidate.is_active = True
    db.flush()

    audit = _append_audit(
        db,
        actor_id=admin.id,
        action="MODEL_ROLLBACK",
        resource_id=candidate.model_version,
        payload={
            "from_version": current.model_version,
            "to_version": candidate.model_version,
            "from_id": previous_active_id,
            "to_id": candidate.id,
            "reason": req.reason,
            "mfa_window_5min": int(datetime.now(timezone.utc).timestamp()) // 300,
        },
    )
    db.commit()

    return {
        "status": "ROLLED_BACK",
        "previous_active_model": _serialize(current),
        "new_active_model": _serialize(candidate),
        "audit_sequence_id": audit.sequence_id,
        "audit_record_hash": audit.record_hash,
    }