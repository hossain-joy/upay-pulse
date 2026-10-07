from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user, require_risk_analyst
from backend.app.models.user import User, UserRole
from backend.app.models.appeal import AppealStatus
from backend.app.schemas.appeal import (
    AppealCreateRequest,
    AppealReviewRequest,
    AppealResponse,
    AppealListResponse
)
from backend.app.services.appeal_service import AppealService
from backend.app.core.exceptions import AppException

router = APIRouter()

@router.post("/submit", response_model=AppealResponse, status_code=status.HTTP_201_CREATED)
def submit_appeal(
    req: AppealCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a citizen false-positive dispute or account lock appeal.
    """
    return AppealService.submit_appeal(db=db, user=current_user, req=req)

@router.get("/my", response_model=AppealListResponse)
def get_my_appeals(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List appeals submitted by the authenticated citizen.
    """
    total, items = AppealService.list_appeals(db=db, user_id=current_user.id, skip=skip, limit=limit)
    return AppealListResponse(total=total, items=items)

@router.get("", response_model=AppealListResponse)
def list_appeals(
    status: Optional[AppealStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_risk_analyst)
):
    """
    List appeals for triage in Risk Console (Risk Analyst / Admin only).
    """
    total, items = AppealService.list_appeals(db=db, status=status, skip=skip, limit=limit)
    return AppealListResponse(total=total, items=items)

@router.get("/{appeal_id}", response_model=AppealResponse)
def get_appeal(
    appeal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get appeal details. Available to the citizen owner or Risk Analyst / Admin.
    """
    appeal = AppealService.get_appeal(db=db, appeal_id=appeal_id)
    if current_user.role not in [UserRole.ADMIN, UserRole.RISK_ANALYST] and appeal.user_id != current_user.id:
        raise AppException("Unauthorized to access this appeal record.", code="FORBIDDEN", status_code=403)
    return appeal

@router.post("/{appeal_id}/review", response_model=AppealResponse)
def review_appeal(
    appeal_id: str,
    req: AppealReviewRequest,
    db: Session = Depends(get_db),
    current_analyst: User = Depends(require_risk_analyst)
):
    """
    Human-in-the-loop review decision: approve and unfreeze or reject.
    Requires RISK_ANALYST or ADMIN role.
    """
    return AppealService.review_appeal(db=db, reviewer=current_analyst, appeal_id=appeal_id, req=req)
