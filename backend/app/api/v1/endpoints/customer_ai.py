from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import require_customer
from backend.app.models.user import User
from backend.app.schemas.customer_ai import (
    CashFlowTrajectoryResponse,
    GraceEligibilityResponse,
    GraceRequestCreate,
    GraceRequestResponse,
    FDRRecommendationResponse,
    FDRCreateRequest,
    FDRResponse
)
from backend.app.services.customer_ai_service import CustomerAIService

router = APIRouter()

@router.get("/trajectory", response_model=CashFlowTrajectoryResponse)
def get_cash_flow_trajectory(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Get 30-day daily balance trajectory, recurring expense forecast, and proactive deficit warning.
    """
    return CustomerAIService.get_trajectory(db=db, user=current_user)

@router.get("/grace/eligibility", response_model=GraceEligibilityResponse)
def get_grace_credit_eligibility(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Get explainable upay Grace micro-overdraft credit rating, approved limit, and decision factors.
    """
    return CustomerAIService.get_grace_eligibility(db=db, user=current_user)

@router.post("/grace/request", response_model=GraceRequestResponse, status_code=status.HTTP_201_CREATED)
def request_grace_advance(
    req: GraceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Request instant disbursement of upay Grace micro-overdraft funds directly into customer wallet.
    """
    return CustomerAIService.request_grace_advance(db=db, user=current_user, req=req)

@router.get("/fdr/recommendation", response_model=FDRRecommendationResponse)
def get_fdr_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Get personalized Micro-FDR options for idle cash with projected annual yields.
    """
    return CustomerAIService.get_fdr_recommendations(db=db, user=current_user)

@router.post("/fdr/create", response_model=FDRResponse, status_code=status.HTTP_201_CREATED)
def create_micro_fdr(
    req: FDRCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Lock idle wallet balance into a high-yield Micro-FDR account (7, 30, or 90 days).
    """
    return CustomerAIService.create_fdr(db=db, user=current_user, req=req)

@router.get("/fdr/accounts", response_model=List[FDRResponse])
def list_micro_fdr_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    List all active and matured Micro-FDR savings accounts.
    """
    return CustomerAIService.list_fdrs(db=db, user=current_user)
