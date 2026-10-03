import enum
from sqlalchemy import Column, String, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class NotificationType(str, enum.Enum):
    SECURITY_ALERT = "SECURITY_ALERT"
    TRANSACTION_UPDATE = "TRANSACTION_UPDATE"
    GRACE_OFFER = "GRACE_OFFER"
    SURGE_WARNING = "SURGE_WARNING"
    FDR_RECOMMENDATION = "FDR_RECOMMENDATION"

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(120), nullable=False)
    message = Column(String(500), nullable=False)
    notification_type = Column(SQLEnum(NotificationType), default=NotificationType.TRANSACTION_UPDATE, nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification user={self.user_id} title={self.title} type={self.notification_type}>"
