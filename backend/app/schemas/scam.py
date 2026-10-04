from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.scam import ScamReportStatus

class ScamReportCreate(BaseModel):
    reported_account: str = Field(..., description="Mobile number, account number, or agent code of scammer")
    transaction_id: Optional[str] = Field(None, description="Optional linked transaction ID")
    reason: str = Field(..., max_length=255, description="Category/reason: Fake lottery, Account takeover, Extortion, etc.")
    investigation_notes: Optional[str] = Field(None, description="Additional victim commentary or evidence")

class ScamReportResolve(BaseModel):
    status: ScamReportStatus = Field(..., description="Target status: CONFIRMED_FRAUD or DISMISSED")
    investigation_notes: Optional[str] = Field(None, description="Investigator notes on findings")
    auto_freeze_account: bool = Field(True, description="If CONFIRMED_FRAUD, immediately invoke Master Freeze on reported account")
    freeze_account: Optional[bool] = Field(None, description="Alias for auto_freeze_account")

    @property
    def execute_freeze(self) -> bool:
        if self.freeze_account is not None:
            return self.freeze_account
        return self.auto_freeze_account

class ScamReportResponse(BaseModel):
    id: str
    reporter_id: str
    reported_account: str
    transaction_id: Optional[str] = None
    reason: str
    status: ScamReportStatus
    cluster_id: Optional[str] = None
    investigation_notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ScamReportListResponse(BaseModel):
    total: int
    items: List[ScamReportResponse]
