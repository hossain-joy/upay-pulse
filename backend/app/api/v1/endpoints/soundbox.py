from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.transaction import Transaction
from backend.app.schemas.soundbox import SoundboxChimeResponse
from backend.app.services.soundbox_service import SoundboxService
from backend.app.core.exceptions import AppException

router = APIRouter()

@router.get("/chime/{transaction_reference}", response_model=SoundboxChimeResponse)
def get_soundbox_chime(
    transaction_reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate auditory chime frequencies and Bengali voice announcement metadata for a settled transaction.
    """
    txn = db.query(Transaction).filter(
        Transaction.transaction_reference == transaction_reference
    ).first()

    if not txn:
        raise AppException("Transaction not found.", code="TRANSACTION_NOT_FOUND", status_code=404)

    return SoundboxService.generate_payment_chime(txn)

@router.get("/chime/{transaction_reference}.wav")
def get_soundbox_chime_wav(
    transaction_reference: str,
    db: Session = Depends(get_db)
):
    """
    Stream generated 16-bit PCM WAV chord audio for physical or software soundbox playback.
    """
    txn = db.query(Transaction).filter(
        Transaction.transaction_reference == transaction_reference
    ).first()
    amount = float(txn.amount) if txn else 500.0
    wav_data = SoundboxService.generate_chime_wav(amount=amount)
    return Response(content=wav_data, media_type="audio/wav")
