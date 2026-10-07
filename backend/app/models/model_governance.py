"""
upay Pulse — Model Governance Registry (Phase 2 §13)
Tracks the active and historical fraud-detection model versions, their evaluation
metrics, and the human approver who signed each into production. Used by the
governance endpoints to expose /api/v1/governance/active-model and to perform
one-click rollback to the previous approved checkpoint.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Numeric, Integer
from backend.app.models.base import Base, TimestampMixin, generate_uuid


class ModelGovernanceRegistry(Base, TimestampMixin):
    __tablename__ = "model_governance_registry"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    model_version = Column(String(64), nullable=False, index=True)
    algorithm = Column(String(128), nullable=False)
    trained_at = Column(DateTime(timezone=True), nullable=False)
    training_dataset = Column(String(128), nullable=True)
    feature_count = Column(Integer, nullable=True)

    # Validation metrics captured at sign-off
    pr_auc = Column(Numeric(8, 6), nullable=False)
    roc_auc = Column(Numeric(8, 6), nullable=False)
    recall_at_1pct_fpr = Column(Numeric(8, 6), nullable=False)
    brier_score = Column(Numeric(8, 6), nullable=False)
    decision_threshold = Column(Numeric(6, 4), nullable=False, default=0.70)

    # Governance
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    approved_by = Column(String(64), nullable=False)
    notes = Column(String(512), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ModelGovernanceRegistry version={self.model_version} "
            f"active={self.is_active} pr_auc={self.pr_auc}>"
        )
