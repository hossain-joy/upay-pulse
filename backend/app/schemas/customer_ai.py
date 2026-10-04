from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.customer_ai import GraceStatus, FDRStatus

class DailyForecastPoint(BaseModel):
    date: str
    day_of_month: int
    inflow_forecast: float
    outflow_forecast: float
    projected_balance: float
    deficit_warning: bool

class DeficitAlertSchema(BaseModel):
    alert_level: str
    days_until_deficit: int
    deficit_date: str
    projected_shortfall: float
    recommended_action: str

class CashFlowTrajectoryResponse(BaseModel):
    current_balance: float
    start_date: str
    has_deficit_alert: bool
    deficit_alert: Optional[DeficitAlertSchema] = None
    projected_30d_end_balance: float
    lowest_projected_balance: float
    highest_projected_balance: float
    daily_forecast: List[DailyForecastPoint]

class GraceEligibilityResponse(BaseModel):
    eligible: bool
    credit_score: int
    approved_limit: float
    current_grace_balance: float
    repayment_likelihood_pct: float
    positive_factors: List[str]
    risk_factors: List[str]
    decision: str
    message: str

class GraceRequestCreate(BaseModel):
    requested_amount: float = Field(..., gt=0.0, le=500.0, description="Requested overdraft loan advance")

class GraceRequestResponse(BaseModel):
    id: str
    customer_id: str
    requested_amount: float
    repaid_amount: float
    status: GraceStatus
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class GraceRepayRequest(BaseModel):
    repay_amount: Optional[float] = Field(None, gt=0.0, description="Amount to repay. If omitted, repays full outstanding grace balance.")

class GraceRepayResponse(BaseModel):
    customer_id: str
    repaid_amount: float
    remaining_grace_balance: float
    new_wallet_balance: float
    message: str

class FDROptionSchema(BaseModel):
    term_days: int
    interest_rate_pct: float
    projected_profit: float
    total_maturity_amount: float

class FDRRecommendationResponse(BaseModel):
    idle_balance_detected: float
    recommended_deposit: float
    minimum_threshold: float
    is_eligible: bool
    options: List[FDROptionSchema]
    message: str

class FDRCreateRequest(BaseModel):
    principal_amount: float = Field(..., ge=10.0, description="Amount to lock into Micro-FDR")
    term_days: int = Field(..., description="Tenure: 7, 30, or 90 days")

class FDRResponse(BaseModel):
    id: str
    customer_id: str
    principal_amount: float
    term_days: int
    interest_rate_pct: float
    start_date: date
    maturity_date: date
    status: FDRStatus
    projected_profit: float
    total_at_maturity: float

    model_config = ConfigDict(from_attributes=True)
