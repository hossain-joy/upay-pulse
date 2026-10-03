from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.transaction import TransactionType, TransactionStatus

class SendMoneyRequest(BaseModel):
    receiver_identifier: str = Field(..., description="Recipient phone number or email")
    amount: float = Field(..., gt=0, description="Amount in BDT (must be positive)")
    category: Optional[str] = Field("General", max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    idempotency_key: Optional[str] = Field(None, max_length=64)
    apply_grace_if_needed: Optional[bool] = Field(False, description="Automatically apply upay Grace if balance shortfall is eligible")

class CashOutRequest(BaseModel):
    agent_identifier: str = Field(..., description="Agent code (e.g. AGT-1001) or agent phone")
    amount: float = Field(..., gt=0, description="Cash-out amount in BDT")
    idempotency_key: Optional[str] = Field(None, max_length=64)

class CashInRequest(BaseModel):
    customer_phone: str = Field(..., description="Recipient customer phone number")
    amount: float = Field(..., gt=0, description="Cash-in amount in BDT")
    idempotency_key: Optional[str] = Field(None, max_length=64)

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transaction_reference: str
    sender_id: Optional[str] = None
    sender_phone: Optional[str] = None
    sender_name: Optional[str] = None
    receiver_id: Optional[str] = None
    receiver_phone: Optional[str] = None
    receiver_name: Optional[str] = None
    agent_id: Optional[str] = None
    agent_code: Optional[str] = None
    amount: float
    fee: float
    transaction_type: TransactionType
    status: TransactionStatus
    category: str
    description: Optional[str] = None
    is_flagged_fraud: bool
    created_at: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    applied_grace_amount: Optional[float] = 0.0

class TransactionHistoryResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
