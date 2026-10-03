from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.freeze import MasterFreezeRequest, MasterFreezeResponse, UnfreezeRequest
from backend.app.api.deps import get_current_user, require_customer
from backend.app.services.freeze_service import MasterFreezeService

router = APIRouter()

@router.post("/trigger", response_model=MasterFreezeResponse, status_code=status.HTTP_200_OK)
def trigger_master_freeze(
    req: MasterFreezeRequest,
    request: Request,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    """
    Emergency Master Freeze mechanism.
    Validates PIN, immediately freezes outgoing transfers, and revokes sessions in sub-300ms SLA.
    """
    client_ip = request.client.host if request.client else None
    return MasterFreezeService.trigger_freeze(
        db=db,
        user=current_user,
        freeze_pin=req.freeze_pin,
        reason=req.reason,
        ip_address=client_ip
    )

@router.get("/status")
def get_freeze_status(
    current_user: User = Depends(get_current_user)
):
    """Check current wallet freeze state."""
    return {
        "user_id": current_user.id,
        "is_frozen": current_user.is_frozen,
        "status": current_user.status.value,
        "failed_pin_attempts": current_user.failed_pin_attempts
    }

@router.post("/unfreeze")
def unfreeze_account(
    req: UnfreezeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verified unfreeze workflow."""
    return MasterFreezeService.unfreeze(
        db=db,
        user=current_user,
        verification_code=req.verification_code
    )
