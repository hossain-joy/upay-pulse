import enum
from sqlalchemy import Column, String, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class ScamReportStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    ANALYZING = "ANALYZING"
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    DISMISSED = "DISMISSED"

class ScamReport(Base, TimestampMixin):
    __tablename__ = "scam_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reporter_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reported_account = Column(String(20), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    reason = Column(String(255), nullable=False)
    status = Column(SQLEnum(ScamReportStatus), default=ScamReportStatus.SUBMITTED, nullable=False, index=True)
    cluster_id = Column(String(64), nullable=True, index=True)
    investigation_notes = Column(Text, nullable=True)

    reporter = relationship("User", foreign_keys=[reporter_id])
    transaction = relationship("Transaction", back_populates="scam_report")

    def __repr__(self):
        return f"<ScamReport reporter={self.reporter_id} target={self.reported_account} status={self.status}>"
