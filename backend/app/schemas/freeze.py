from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class MasterFreezeRequest(BaseModel):
    freeze_pin: str = Field(..., min_length=4, max_length=6, description="4-6 digit emergency Master Freeze PIN")
    reason: Optional[str] = Field("Suspected device theft or unauthorized account access", max_length=255)

class MasterFreezeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    is_frozen: bool
    sessions_revoked: int
    pending_cancelled: int
    response_time_ms: float
    message: str
    target_sla_met: bool  # True if < 300ms

class UnfreezeRequest(BaseModel):
    verification_code: str = Field(..., description="SMS OTP or Administrator verification code")
    admin_notes: Optional[str] = None
