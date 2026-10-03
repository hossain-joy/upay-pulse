from sqlalchemy import Column, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class CustomerProfile(Base, TimestampMixin):
    __tablename__ = "customer_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    profession = Column(String(60), default="General", nullable=False)
    location = Column(String(100), default="Dhaka", nullable=False)
    
    # Financial Balances (Simulated BDT)
    wallet_balance = Column(Numeric(14, 2), default=0.00, nullable=False)
    grace_balance = Column(Numeric(14, 2), default=0.00, nullable=False)
    reliability_score = Column(Numeric(4, 2), default=0.85, nullable=False)
    
    # Behavioral Baselines
    avg_monthly_inflow = Column(Numeric(14, 2), default=15000.00, nullable=False)
    avg_monthly_outflow = Column(Numeric(14, 2), default=14000.00, nullable=False)
    spending_pattern = Column(String(255), default="Balanced", nullable=False)

    # Relationships
    user = relationship("User", back_populates="customer_profile")
    grace_requests = relationship("GraceOverdraftRequest", back_populates="customer", cascade="all, delete-orphan")
    cash_flow_forecasts = relationship("CashFlowForecast", back_populates="customer", cascade="all, delete-orphan")
    micro_fdr_accounts = relationship("MicroFDRAccount", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CustomerProfile name={self.full_name} balance={self.wallet_balance}>"
