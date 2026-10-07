import enum
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid, utc_now

class AppealCategory(str, enum.Enum):
    EMERGENCY_MEDICAL = "EMERGENCY_MEDICAL"
    FAMILY_REMITTANCE = "FAMILY_REMITTANCE"
    BUSINESS_PAYMENT = "BUSINESS_PAYMENT"
    FALSE_POSITIVE_FLAG = "FALSE_POSITIVE_FLAG"
    ACCOUNT_FROZEN_DISPUTE = "ACCOUNT_FROZEN_DISPUTE"
    OTHER = "OTHER"

class AppealStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class AppealReviewAction(str, enum.Enum):
    UNFREEZE_ACCOUNT = "UNFREEZE_ACCOUNT"
    WHITELIST_BENEFICIARY = "WHITELIST_BENEFICIARY"
    OVERRIDE_FLAG = "OVERRIDE_FLAG"
    MAINTAIN_BLOCK = "MAINTAIN_BLOCK"

class Appeal(Base, TimestampMixin):
    __tablename__ = "appeals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_reference = Column(String(64), nullable=True, index=True)
    category = Column(SQLEnum(AppealCategory), default=AppealCategory.FALSE_POSITIVE_FLAG, nullable=False, index=True)
    status = Column(SQLEnum(AppealStatus), default=AppealStatus.PENDING, nullable=False, index=True)
    
    explanation = Column(Text, nullable=False)
    supporting_document_ref = Column(String(255), nullable=True)
    
    reviewed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_action = Column(SQLEnum(AppealReviewAction), nullable=True)
    review_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f"<Appeal id={self.id} user={self.user_id} status={self.status} category={self.category}>"
