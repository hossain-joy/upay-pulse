import enum
from sqlalchemy import Column, String, Numeric, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class RiskDecision(str, enum.Enum):
    ALLOW = "ALLOW"
    FRICTION_CHALLENGE = "FRICTION_CHALLENGE"
    BLOCK_AND_FLAG = "BLOCK_AND_FLAG"

class RiskScore(Base, TimestampMixin):
    __tablename__ = "risk_scores"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    risk_score = Column(Numeric(4, 3), nullable=False, index=True)
    risk_level = Column(SQLEnum(RiskLevel), nullable=False, index=True)
    decision = Column(SQLEnum(RiskDecision), nullable=False, index=True)
    
    reasons = Column(Text, nullable=True)  # JSON formatted key drivers
    feature_vector = Column(Text, nullable=True)  # JSON formatted feature snapshot
    inference_latency_ms = Column(Numeric(6, 2), default=0.00, nullable=False)

    transaction = relationship("Transaction", back_populates="risk_score")

    def __repr__(self):
        return f"<RiskScore score={self.risk_score} level={self.risk_level} decision={self.decision}>"
