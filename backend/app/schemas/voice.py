from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class VoiceQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Voice query text in Bengali or English")
    language: str = Field("bn", description="Language code (default: 'bn' for Bengali)")

class VoiceQueryResponse(BaseModel):
    session_id: str
    query_text: str
    response_bangla: str
    intent: str
    latency_ms: float
    audio_url: Optional[str] = None
    context_summary: Dict[str, Any]

class VoiceSessionHistoryItem(BaseModel):
    id: str
    query_text: str
    response_bangla: str
    intent: str
    latency_ms: float
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
