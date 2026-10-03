from typing import Optional
from pydantic import BaseModel, Field

class DynamicBadgeResponse(BaseModel):
    transaction_reference: str
    amount: float
    recipient_name: str
    category: Optional[str] = None
    status: str
    dynamic_nonce: str
    pulse_color: str
    pulse_frequency_hz: float
    seconds_remaining_in_window: int
    created_at: Optional[str] = None
    security_disclaimer: str

class BadgeVerifyRequest(BaseModel):
    transaction_reference: str = Field(..., description="Transaction reference number")
    nonce: str = Field(..., min_length=4, max_length=10, description="Cryptographic dynamic nonce from badge")

class BadgeVerifyResponse(BaseModel):
    is_valid: bool
    verification_status: str
    transaction_reference: Optional[str] = None
    amount: Optional[float] = None
    created_at: Optional[str] = None
    message: str
