import enum
from sqlalchemy import Column, String, Numeric, Boolean, Date, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class GraceStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REPAID = "REPAID"
    DEFAULTED = "DEFAULTED"

class FDRStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MATURED = "MATURED"
    PRE_CLOSED = "PRE_CLOSED"

class CashFlowForecast(Base, TimestampMixin):
    __tablename__ = "cash_flow_forecasts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    
    inflow_forecast = Column(Numeric(14, 2), default=0.00, nullable=False)
    outflow_forecast = Column(Numeric(14, 2), default=0.00, nullable=False)
    projected_balance = Column(Numeric(14, 2), default=0.00, nullable=False)
    deficit_warning = Column(Boolean, default=False, nullable=False)

    customer = relationship("CustomerProfile", back_populates="cash_flow_forecasts")

class GraceOverdraftRequest(Base, TimestampMixin):
    __tablename__ = "grace_overdraft_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    requested_amount = Column(Numeric(14, 2), nullable=False)
    repaid_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    status = Column(SQLEnum(GraceStatus), default=GraceStatus.APPROVED, nullable=False, index=True)

    customer = relationship("CustomerProfile", back_populates="grace_requests")

class MicroFDRAccount(Base, TimestampMixin):
    __tablename__ = "micro_fdr_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    principal_amount = Column(Numeric(14, 2), nullable=False)
    term_days = Column(Numeric(5, 0), default=30, nullable=False)
    interest_rate_pct = Column(Numeric(4, 2), default=7.50, nullable=False)
    
    start_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    status = Column(SQLEnum(FDRStatus), default=FDRStatus.ACTIVE, nullable=False, index=True)

    customer = relationship("CustomerProfile", back_populates="micro_fdr_accounts")
