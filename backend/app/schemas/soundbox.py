from typing import List, Optional
from pydantic import BaseModel

class SoundboxChimeResponse(BaseModel):
    transaction_reference: str
    amount: float
    amount_bangla: str
    vocal_script_bangla: str
    vocal_script_english: str
    chime_tone_frequency_hz: List[float]
    chime_duration_ms: int
    audio_url: str
    soundbox_status: str
