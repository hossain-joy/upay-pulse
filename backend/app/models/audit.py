from sqlalchemy import Column, String, Text
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_id = Column(String(36), nullable=True, index=True)
    actor_role = Column(String(30), default="SYSTEM", nullable=False, index=True)
    
    action = Column(String(80), nullable=False, index=True)  # e.g., "MASTER_FREEZE", "TRANSACTION_BLOCK", "GRACE_APPROVAL"
    resource = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(64), nullable=True, index=True)
    
    details = Column(Text, nullable=True)  # JSON formatted context
    ip_address = Column(String(45), nullable=True)
    status = Column(String(20), default="SUCCESS", nullable=False)

    def __repr__(self):
        return f"<AuditLog actor={self.actor_id} action={self.action} resource={self.resource}>"
