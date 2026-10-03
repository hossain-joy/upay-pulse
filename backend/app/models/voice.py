from sqlalchemy import Column, String, Numeric, Text, ForeignKey
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class VoiceCoachSession(Base, TimestampMixin):
    __tablename__ = "voice_coach_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    query_text = Column(String(500), nullable=False)
    response_bangla = Column(Text, nullable=False)
    audio_url = Column(String(255), nullable=True)
    intent = Column(String(50), default="SPENDING_INSIGHT", nullable=False)
    latency_ms = Column(Numeric(6, 2), default=0.00, nullable=False)

    def __repr__(self):
        return f"<VoiceCoachSession customer={self.customer_id} intent={self.intent}>"
