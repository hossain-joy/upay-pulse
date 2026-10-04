from typing import List, Optional
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
    GraceRepayRequest,
    GraceRepayResponse,
    FDRRecommendationResponse,
    FDRCreateRequest,
    FDRResponse
)
from backend.app.schemas.voice import (
    VoiceQueryRequest,
    VoiceQueryResponse,
    VoiceSessionHistoryItem
)
from backend.app.services.customer_ai_service import CustomerAIService
from backend.app.services.voice_coach_service import VoiceCoachService

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

@router.post("/grace/repay", response_model=GraceRepayResponse)
def repay_grace_advance(
    req: Optional[GraceRepayRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Repay active upay Grace micro-overdraft loan directly from wallet balance to restore credit limit.
    """
    return CustomerAIService.repay_grace_advance(db=db, user=current_user, req=req)

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

@router.post("/fdr/{fdr_id}/liquidate")
def liquidate_micro_fdr(
    fdr_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Liquidate an active or matured Micro-FDR account and refund principal + earned profit to wallet.
    """
    return CustomerAIService.liquidate_fdr(db=db, user=current_user, fdr_id=fdr_id)

@router.post("/voice-coach/chat", response_model=VoiceQueryResponse)
def voice_coach_chat(
    req: VoiceQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Conversational financial advisory in natural Bengali with live wallet context injection.
    """
    return VoiceCoachService.process_query(db=db, user=current_user, req=req)

@router.get("/voice-coach/history", response_model=List[VoiceSessionHistoryItem])
def voice_coach_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Retrieve past voice coach consultation history.
    """
    return VoiceCoachService.get_history(db=db, user=current_user)

@router.get("/voice-coach/audio/{session_id}")
def get_voice_coach_audio(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Serve synthesized PCM WAV audio chime for voice coach interaction.
    """
    from fastapi import Response
    from backend.app.services.soundbox_service import SoundboxService
    wav_bytes = SoundboxService.generate_chime_wav(amount=100.0)
    return Response(content=wav_bytes, media_type="audio/wav")

