import enum
from sqlalchemy import Column, String, Integer, Numeric, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class FreezeActionType(str, enum.Enum):
    MASTER_FREEZE_TRIGGERED = "MASTER_FREEZE_TRIGGERED"
    MANUAL_ADMIN_FREEZE = "MANUAL_ADMIN_FREEZE"
    UNFREEZE_VERIFIED = "UNFREEZE_VERIFIED"

class FreezeAction(Base, TimestampMixin):
    __tablename__ = "freeze_actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(SQLEnum(FreezeActionType), default=FreezeActionType.MASTER_FREEZE_TRIGGERED, nullable=False, index=True)
    
    sessions_revoked = Column(Integer, default=0, nullable=False)
    pending_cancelled = Column(Integer, default=0, nullable=False)
    response_time_ms = Column(Numeric(6, 2), default=0.00, nullable=False)
    ip_address = Column(String(45), nullable=True)
    reason = Column(String(255), nullable=True)

    user = relationship("User", back_populates="freeze_actions")

    def __repr__(self):
        return f"<FreezeAction user={self.user_id} type={self.action_type} latency={self.response_time_ms}ms>"
