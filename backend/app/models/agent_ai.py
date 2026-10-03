from sqlalchemy import Column, String, Numeric, Integer, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class AgentLiquidityForecast(Base, TimestampMixin):
    __tablename__ = "agent_liquidity_forecasts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_id = Column(String(36), ForeignKey("agent_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    target_date = Column(Date, nullable=False, index=True)
    hour_of_day = Column(Integer, default=12, nullable=False)
    
    predicted_cash_out = Column(Numeric(14, 2), default=0.00, nullable=False)
    recommended_float = Column(Numeric(14, 2), default=0.00, nullable=False)
    surge_flag = Column(Boolean, default=False, nullable=False, index=True)
    surge_reason = Column(String(255), nullable=True)

    agent = relationship("AgentProfile", back_populates="liquidity_forecasts")

    def __repr__(self):
        return f"<AgentLiquidityForecast agent={self.agent_id} date={self.target_date} surge={self.surge_flag}>"
