from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class DailyLiquidityPoint(BaseModel):
    date: str
    day_of_week: str
    predicted_cash_out: float
    recommended_float: float
    surge_flag: bool
    surge_reason: Optional[str] = None

class RebalanceSuggestion(BaseModel):
    action: str = Field(..., description="CONVERT_FLOAT_TO_CASH, CONVERT_CASH_TO_FLOAT, or OPTIMAL")
    recommended_amount: float
    reason: str

class AgentLiquidityForecastResponse(BaseModel):
    agent_code: str
    store_name: str
    location_cluster: str
    is_factory_zone: bool
    current_cash_balance: float
    current_float_balance: float
    total_7d_predicted_cash_out: float
    stockout_risk: str = Field(..., description="CRITICAL, ELEVATED, MODERATE, LOW")
    days_until_stockout: Optional[int] = None
    rebalance_suggestion: RebalanceSuggestion
    daily_forecast: List[DailyLiquidityPoint]

class RebalanceRequest(BaseModel):
    action: str = Field(..., description="FLOAT_TO_CASH or CASH_TO_FLOAT")
    amount: float = Field(..., gt=0.0, description="Amount in BDT to rebalance")

class RebalanceResponse(BaseModel):
    agent_code: str
    action: str
    amount: float
    previous_cash: float
    new_cash: float
    previous_float: float
    new_float: float
    message: str
