from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.appeal import AppealCategory, AppealStatus, AppealReviewAction

class AppealCreateRequest(BaseModel):
    category: AppealCategory = Field(default=AppealCategory.FALSE_POSITIVE_FLAG, description="Dispute category")
    explanation: str = Field(..., min_length=10, max_length=1000, description="Detailed explanation of the false positive transaction or freeze")
    transaction_reference: Optional[str] = Field(None, max_length=64, description="Optional transaction reference ID")
    supporting_document_ref: Optional[str] = Field(None, max_length=255, description="Reference ID for supporting proof (e.g. medical bill, hospital receipt, KYC doc)")

class AppealReviewRequest(BaseModel):
    action: AppealReviewAction = Field(..., description="Triage decision action: UNFREEZE_ACCOUNT, WHITELIST_BENEFICIARY, OVERRIDE_FLAG, MAINTAIN_BLOCK")
    review_notes: str = Field(..., min_length=5, max_length=1000, description="Mandatory analyst reasoning and justification for audit log")

class AppealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    user_phone: Optional[str] = None
    user_email: Optional[str] = None
    category: AppealCategory
    status: AppealStatus
    explanation: str
    transaction_reference: Optional[str] = None
    supporting_document_ref: Optional[str] = None
    reviewed_by_id: Optional[str] = None
    reviewer_email: Optional[str] = None
    review_action: Optional[AppealReviewAction] = None
    review_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

class AppealListResponse(BaseModel):
    total: int
    items: List[AppealResponse]
