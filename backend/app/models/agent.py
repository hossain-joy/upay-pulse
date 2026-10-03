from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class AgentProfile(Base, TimestampMixin):
    __tablename__ = "agent_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    agent_code = Column(String(20), unique=True, nullable=False, index=True)
    store_name = Column(String(120), nullable=False)
    location_cluster = Column(String(100), default="Dhaka Central", nullable=False, index=True)
    
    # Operational Liquidity
    cash_balance = Column(Numeric(14, 2), default=50000.00, nullable=False)
    float_balance = Column(Numeric(14, 2), default=100000.00, nullable=False)
    daily_cash_out_volume = Column(Numeric(14, 2), default=0.00, nullable=False)
    is_factory_zone = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="agent_profile")
    liquidity_forecasts = relationship("AgentLiquidityForecast", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AgentProfile code={self.agent_code} store={self.store_name} cash={self.cash_balance}>"
