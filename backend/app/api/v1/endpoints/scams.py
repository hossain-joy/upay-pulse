from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user, require_admin
from backend.app.models.user import User, UserRole
from backend.app.models.scam import ScamReportStatus
from backend.app.schemas.scam import (
    ScamReportCreate,
    ScamReportResolve,
    ScamReportResponse,
    ScamReportListResponse
)
from backend.app.services.scam_service import ScamService
from backend.app.core.exceptions import AppException

router = APIRouter()

@router.post("/report", response_model=ScamReportResponse, status_code=status.HTTP_201_CREATED)
def file_scam_report(
    req: ScamReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a citizen or agent scam report against a suspected fraudster/mule.
    """
    return ScamService.file_report(db=db, reporter=current_user, req=req)

@router.get("/reports", response_model=ScamReportListResponse)
def list_scam_reports(
    status: Optional[ScamReportStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    List filed scam reports (Admin / Risk Console only).
    """
    total, items = ScamService.list_reports(db=db, status=status, skip=skip, limit=limit)
    return ScamReportListResponse(total=total, items=items)

@router.get("/reports/{report_id}", response_model=ScamReportResponse)
def get_scam_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve single scam report details.
    """
    report = ScamService.get_report(db=db, report_id=report_id)
    if current_user.role != UserRole.ADMIN and report.reporter_id != current_user.id:
        raise AppException(
            message="Unauthorized to view this report.",
            code="UNAUTHORIZED",
            status_code=403
        )
    return report

@router.post("/reports/{report_id}/resolve", response_model=ScamReportResponse)
def resolve_scam_report(
    report_id: str,
    req: ScamReportResolve,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Resolve a scam report and optionally trigger automated Master Freeze (Admin only).
    """
    return ScamService.resolve_report(db=db, report_id=report_id, admin=current_admin, req=req)
