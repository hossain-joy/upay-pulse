"""
upay Pulse - Voice Coach Service
Coordinates conversational AI queries in Bengali, injects real-time financial context,
persists coaching sessions, and generates speech synthesis metadata.
"""

import time
import secrets
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.exceptions import AppException
from backend.app.models.user import User
from backend.app.models.customer import CustomerProfile
from backend.app.models.voice import VoiceCoachSession
from backend.app.schemas.voice import VoiceQueryRequest, VoiceQueryResponse
from backend.app.services.ai_provider import get_ai_provider
from backend.app.services.customer_ai_service import CustomerAIService

class VoiceCoachService:

    @classmethod
    def process_query(cls, db: Session, user: User, req: VoiceQueryRequest) -> VoiceQueryResponse:
        """
        Receives customer query, aggregates live financial context, executes LLM generation,
        and records session history.
        """
        profile: CustomerProfile = user.customer_profile
        if not profile:
            raise AppException("Customer profile required for voice coach.", code="PROFILE_MISSING", status_code=400)

        # 1. Fetch live financial context
        trajectory = CustomerAIService.get_trajectory(db, user)
        grace_eligibility = CustomerAIService.get_grace_eligibility(db, user)

        context = {
            "full_name": profile.full_name,
            "profession": profile.profession or "General",
            "wallet_balance": float(profile.wallet_balance),
            "grace_balance": float(profile.grace_balance),
            "approved_grace_limit": grace_eligibility.get("approved_limit", 50.0),
            "spending_pattern": profile.spending_pattern or "নিত্যপ্রয়োজনীয় খরচ",
            "has_deficit_alert": trajectory.get("has_deficit_alert", False),
            "deficit_date": trajectory.get("deficit_alert", {}).get("deficit_date") if trajectory.get("has_deficit_alert") else None,
            "reliability_score": float(profile.reliability_score)
        }

        # 2. Execute AI Provider with latency benchmark
        t_start = time.perf_counter()
        provider = get_ai_provider()
        response_text, intent = provider.generate_financial_advice(req.query, context)
        latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        # 3. Persist coaching session in database
        session_id = str(secrets.token_hex(16))
        audio_url = f"/api/v1/customer-ai/voice-coach/audio/{session_id}"

        db_session = VoiceCoachSession(
            id=session_id,
            customer_id=user.id,
            query_text=req.query.strip(),
            response_bangla=response_text,
            audio_url=audio_url,
            intent=intent,
            latency_ms=Decimal(str(latency_ms))
        )
        db.add(db_session)
        db.commit()

        return VoiceQueryResponse(
            session_id=session_id,
            query_text=req.query.strip(),
            response_bangla=response_text,
            intent=intent,
            latency_ms=latency_ms,
            audio_url=audio_url,
            context_summary={
                "wallet_balance": context["wallet_balance"],
                "grace_limit": context["approved_grace_limit"],
                "has_deficit_alert": context["has_deficit_alert"]
            }
        )

    @classmethod
    def get_history(cls, db: Session, user: User, limit: int = 20) -> List[VoiceCoachSession]:
        """
        Retrieves recent voice coaching interaction history for customer.
        """
        return db.query(VoiceCoachSession).filter(
            VoiceCoachSession.customer_id == user.id
        ).order_by(desc(VoiceCoachSession.created_at)).limit(limit).all()
