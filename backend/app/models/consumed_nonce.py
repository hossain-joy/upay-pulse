"""
upay Pulse — Consumed Nonce Ledger (Phase 2 §13)
Persists dynamic anti-screenshot nonces that have been successfully redeemed at
a merchant counter so the live replay-defense query path is durable across
worker restarts (BadgeService also keeps a fast in-memory set for sub-ms
rejection; this table is the auditable record).
"""

from sqlalchemy import Column, String, DateTime, Index
from backend.app.models.base import Base, TimestampMixin, generate_uuid


class ConsumedNonce(Base, TimestampMixin):
    __tablename__ = "consumed_nonces"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    nonce_code = Column(String(32), nullable=False, unique=True, index=True)
    transaction_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    merchant_id = Column(String(64), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    def __repr__(self) -> str:
        return (
            f"<ConsumedNonce nonce={self.nonce_code} txn={self.transaction_id} "
            f"merchant={self.merchant_id}>"
        )


Index(
    "ix_consumed_nonces_nonce_txn",
    ConsumedNonce.nonce_code,
    ConsumedNonce.transaction_id,
    unique=True,
)
