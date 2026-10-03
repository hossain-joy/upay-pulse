import enum
from sqlalchemy import Column, String, Numeric, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class TransactionType(str, enum.Enum):
    SEND_MONEY = "SEND_MONEY"
    CASH_IN = "CASH_IN"
    CASH_OUT = "CASH_OUT"
    MERCHANT_PAY = "MERCHANT_PAY"
    BILL_PAY = "BILL_PAY"
    RECHARGE = "RECHARGE"

class TransactionStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    PENDING_REVIEW = "PENDING_REVIEW"
    BLOCKED = "BLOCKED"
    CANCELLED_FREEZE = "CANCELLED_FREEZE"

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transaction_reference = Column(String(32), unique=True, nullable=False, index=True)
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)
    
    sender_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    receiver_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    amount = Column(Numeric(14, 2), nullable=False)
    fee = Column(Numeric(14, 2), default=0.00, nullable=False)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False, index=True)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.COMPLETED, nullable=False, index=True)
    
    category = Column(String(50), default="General", nullable=False)
    description = Column(String(255), nullable=True)
    is_flagged_fraud = Column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    agent = relationship("User", foreign_keys=[agent_id])
    risk_score = relationship("RiskScore", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    scam_report = relationship("ScamReport", back_populates="transaction", uselist=False)

    def __repr__(self):
        return f"<Transaction ref={self.transaction_reference} amount={self.amount} type={self.transaction_type} status={self.status}>"
