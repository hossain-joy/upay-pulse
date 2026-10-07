"""
upay Pulse — Immutable Security Audit Chain (Phase 2 §13)
Append-only ledger of security-sensitive operations. Each row contains a
SHA-256 record_hash computed over (previous_hash + canonical JSON of the
payload), forming a tamper-evident chain. There is intentionally no
`update` or `delete` path; the only write operation is append.
"""

import hashlib
import json
from sqlalchemy import Column, String, DateTime, BigInteger, Index, JSON
from backend.app.models.base import Base, TimestampMixin, generate_uuid, utc_now


def _canonical_payload(payload: dict) -> str:
    """Deterministic JSON encoding for hashing (sort_keys, separators fixed)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_record_hash(previous_hash: str, payload: dict) -> str:
    """Compute SHA-256 chain hash. Exposed for use by writers/tests."""
    blob = f"{previous_hash}:{_canonical_payload(payload)}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class ImmutableSecurityAudit(Base, TimestampMixin):
    __tablename__ = "immutable_security_audit"

    sequence_id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    actor_id = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    resource_id = Column(String(64), nullable=False, index=True)
    previous_hash = Column(String(64), nullable=False)
    record_hash = Column(String(64), nullable=False, unique=True, index=True)
    # Use generic JSON for SQLite/Postgres portability; on PG this maps to JSONB.
    payload_json = Column(JSON, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ImmutableSecurityAudit seq={self.sequence_id} action={self.action} "
            f"actor={self.actor_id}>"
        )


Index(
    "ix_immutable_security_audit_actor_action",
    ImmutableSecurityAudit.actor_id,
    ImmutableSecurityAudit.action,
)
