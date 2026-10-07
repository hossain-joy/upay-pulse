"""
upay Pulse — Citizen False-Positive Dispute & Human-in-the-Loop Triage Service
Allows blocked/flagged citizens to submit appeals with evidence, and enables
Risk Analysts to review, investigate, and safely unfreeze legitimate users with audit logging.
"""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.user import User, UserStatus
from backend.app.models.appeal import Appeal, AppealCategory, AppealStatus, AppealReviewAction
from backend.app.models.freeze import FreezeAction, FreezeActionType
from backend.app.models.audit import AuditLog
from backend.app.models.base import utc_now
from backend.app.schemas.appeal import AppealCreateRequest, AppealReviewRequest, AppealResponse
from backend.app.core.exceptions import AppException
from backend.app.core.events import event_bus

class AppealService:

    @classmethod
    def submit_appeal(cls, db: Session, user: User, req: AppealCreateRequest) -> AppealResponse:
        appeal = Appeal(
            user_id=user.id,
            category=req.category,
            explanation=req.explanation,
            transaction_reference=req.transaction_reference,
            supporting_document_ref=req.supporting_document_ref,
            status=AppealStatus.PENDING
        )
        db.add(appeal)
        db.commit()
        db.refresh(appeal)

        # Dispatch async event for Risk Console real-time notification
        try:
            event_bus.publish_sync("appeal:submitted", {
                "appeal_id": appeal.id,
                "user_phone": user.phone,
                "category": appeal.category.value,
                "created_at": appeal.created_at.isoformat() if appeal.created_at else None
            })
        except Exception:
            pass

        return cls._format_response(appeal)

    @classmethod
    def list_appeals(
        cls,
        db: Session,
        status: Optional[AppealStatus] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[int, List[AppealResponse]]:
        query = db.query(Appeal)
        if status:
            query = query.filter(Appeal.status == status)
        if user_id:
            query = query.filter(Appeal.user_id == user_id)
        
        total = query.count()
        items = query.order_by(Appeal.created_at.desc()).offset(skip).limit(limit).all()
        return total, [cls._format_response(item) for item in items]

    @classmethod
    def get_appeal(cls, db: Session, appeal_id: str) -> AppealResponse:
        appeal = db.query(Appeal).filter(Appeal.id == appeal_id).first()
        if not appeal:
            raise AppException("Appeal not found.", code="APPEAL_NOT_FOUND", status_code=404)
        return cls._format_response(appeal)

    @classmethod
    def review_appeal(
        cls,
        db: Session,
        reviewer: User,
        appeal_id: str,
        req: AppealReviewRequest
    ) -> AppealResponse:
        appeal = db.query(Appeal).filter(Appeal.id == appeal_id).first()
        if not appeal:
            raise AppException("Appeal not found.", code="APPEAL_NOT_FOUND", status_code=404)

        if appeal.status in [AppealStatus.APPROVED, AppealStatus.REJECTED]:
            raise AppException("Appeal has already been resolved and cannot be re-triaged.", code="ALREADY_RESOLVED", status_code=400)

        # Determine outcome
        if req.action in [AppealReviewAction.UNFREEZE_ACCOUNT, AppealReviewAction.WHITELIST_BENEFICIARY, AppealReviewAction.OVERRIDE_FLAG]:
            appeal.status = AppealStatus.APPROVED
            
            # If action unfreezes account, restore user status
            if req.action == AppealReviewAction.UNFREEZE_ACCOUNT:
                target_user = db.query(User).filter(User.id == appeal.user_id).first()
                if target_user:
                    target_user.is_frozen = False
                    target_user.status = UserStatus.ACTIVE
                    target_user.failed_pin_attempts = 0
                    
                    db.add(FreezeAction(
                        user_id=target_user.id,
                        action_type=FreezeActionType.UNFREEZE_VERIFIED,
                        reason=f"Human-in-the-loop appeal {appeal.id} approved: {req.review_notes}",
                        response_time_ms=0.0
                    ))
        else:
            appeal.status = AppealStatus.REJECTED

        appeal.reviewed_by_id = reviewer.id
        appeal.review_action = req.action
        appeal.review_notes = req.review_notes
        appeal.resolved_at = utc_now()

        # Mandatory Audit Log Entry
        db.add(AuditLog(
            actor_id=reviewer.id,
            actor_role=reviewer.role.value if hasattr(reviewer.role, "value") else str(reviewer.role),
            action="APPEAL_REVIEWED",
            resource="APPEAL",
            resource_id=appeal.id,
            details=f'{{"action": "{req.action.value}", "user_id": "{appeal.user_id}", "status": "{appeal.status.value}", "notes": "{req.review_notes}"}}'
        ))

        db.commit()
        db.refresh(appeal)

        try:
            event_bus.publish_sync("appeal:reviewed", {
                "appeal_id": appeal.id,
                "status": appeal.status.value,
                "action": req.action.value,
                "reviewer": reviewer.email
            })
        except Exception:
            pass

        return cls._format_response(appeal)

    @classmethod
    def _format_response(cls, appeal: Appeal) -> AppealResponse:
        return AppealResponse(
            id=appeal.id,
            user_id=appeal.user_id,
            user_phone=appeal.user.phone if appeal.user else None,
            user_email=appeal.user.email if appeal.user else None,
            category=appeal.category,
            status=appeal.status,
            explanation=appeal.explanation,
            transaction_reference=appeal.transaction_reference,
            supporting_document_ref=appeal.supporting_document_ref,
            reviewed_by_id=appeal.reviewed_by_id,
            reviewer_email=appeal.reviewer.email if appeal.reviewer else None,
            review_action=appeal.review_action,
            review_notes=appeal.review_notes,
            created_at=appeal.created_at,
            resolved_at=appeal.resolved_at
        )
