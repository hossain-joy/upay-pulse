from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import require_agent
from backend.app.models.user import User
from backend.app.schemas.agent_ai import (
    AgentLiquidityForecastResponse,
    RebalanceRequest,
    RebalanceResponse
)
from backend.app.services.agent_ai_service import AgentAIService

router = APIRouter()

@router.get("/forecast", response_model=AgentLiquidityForecastResponse)
def get_agent_liquidity_forecast(
    db: Session = Depends(get_db),
    current_agent: User = Depends(require_agent)
):
    """
    Get 7-day predicted cash-out demand, stockout risk assessment, and float rebalancing instructions.
    """
    return AgentAIService.get_forecast(db=db, user=current_agent)

@router.post("/rebalance", response_model=RebalanceResponse)
def rebalance_agent_liquidity(
    req: RebalanceRequest,
    db: Session = Depends(get_db),
    current_agent: User = Depends(require_agent)
):
    """
    Execute simulated operational liquidity rebalancing between physical cash drawer and digital float.
    """
    return AgentAIService.rebalance(db=db, user=current_agent, req=req)
