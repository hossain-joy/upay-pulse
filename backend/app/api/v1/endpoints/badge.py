from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.badge import (
    DynamicBadgeResponse,
    BadgeVerifyRequest,
    BadgeVerifyResponse
)
from backend.app.services.badge_service import BadgeService

router = APIRouter()

@router.get("/generate/{transaction_reference}", response_model=DynamicBadgeResponse)
def generate_payment_badge(
    transaction_reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate dynamic cryptographic nonce and visual pulse parameters for anti-screenshot payment badge.
    """
    return BadgeService.generate_badge(db=db, transaction_reference=transaction_reference)

@router.post("/verify", response_model=BadgeVerifyResponse)
def verify_payment_badge(
    req: BadgeVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Merchant/Agent verification endpoint: validates presented badge nonce against Central Ledger.
    Detects static screenshots, recordings, and counterfeit receipts.
    """
    return BadgeService.verify_badge(
        db=db,
        transaction_reference=req.transaction_reference,
        nonce=req.nonce
    )
