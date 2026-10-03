import uuid
import secrets
import json
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from backend.app.core.exceptions import AppException
from backend.app.core.events import event_bus
from backend.app.models.user import User, UserRole, UserStatus
from backend.app.models.customer import CustomerProfile
from backend.app.models.agent import AgentProfile
from backend.app.models.transaction import Transaction, TransactionType, TransactionStatus
from backend.app.models.risk import RiskScore, RiskLevel, RiskDecision
from backend.app.models.customer_ai import GraceOverdraftRequest, GraceStatus
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.audit import AuditLog
from backend.app.schemas.transaction import (
    SendMoneyRequest,
    CashOutRequest,
    CashInRequest,
    TransactionResponse
)

def generate_transaction_reference() -> str:
    """Generate a unique reference string, e.g. TXN-8F92AC4E."""
    return f"TXN-{secrets.token_hex(4).upper()}"

def format_transaction_response(txn: Transaction, applied_grace: float = 0.0) -> TransactionResponse:
    """Format SQLAlchemy Transaction model to Pydantic TransactionResponse."""
    sender_phone = txn.sender.phone if txn.sender else None
    sender_name = txn.sender.customer_profile.full_name if (txn.sender and txn.sender.customer_profile) else None
    receiver_phone = txn.receiver.phone if txn.receiver else None
    receiver_name = txn.receiver.customer_profile.full_name if (txn.receiver and txn.receiver.customer_profile) else None
    agent_code = txn.agent.agent_profile.agent_code if (txn.agent and txn.agent.agent_profile) else None

    risk_val = float(txn.risk_score.risk_score) if txn.risk_score else 0.05
    risk_tier = txn.risk_score.risk_level.value if txn.risk_score else "LOW"

    return TransactionResponse(
        id=txn.id,
        transaction_reference=txn.transaction_reference,
        sender_id=txn.sender_id,
        sender_phone=sender_phone,
        sender_name=sender_name,
        receiver_id=txn.receiver_id,
        receiver_phone=receiver_phone,
        receiver_name=receiver_name,
        agent_id=txn.agent_id,
        agent_code=agent_code,
        amount=float(txn.amount),
        fee=float(txn.fee),
        transaction_type=txn.transaction_type,
        status=txn.status,
        category=txn.category,
        description=txn.description,
        is_flagged_fraud=txn.is_flagged_fraud,
        created_at=txn.created_at.isoformat() if txn.created_at else "",
        risk_score=risk_val,
        risk_level=risk_tier,
        applied_grace_amount=applied_grace
    )

class TransactionService:

    @staticmethod
    def send_money(db: Session, sender: User, req: SendMoneyRequest) -> TransactionResponse:
        """Process peer-to-peer or customer-to-merchant simulated money transfer."""
        if sender.is_frozen or sender.status == UserStatus.FROZEN:
            raise AppException(
                message="Your account is locked by Master Freeze. Outgoing transfers are disabled.",
                code="ACCOUNT_FROZEN",
                status_code=403
            )

        # 1. Idempotency Check
        if req.idempotency_key:
            existing = db.query(Transaction).filter(Transaction.idempotency_key == req.idempotency_key).first()
            if existing:
                return format_transaction_response(existing)

        # 2. Resolve Recipient
        receiver_identifier = req.receiver_identifier.strip()
        receiver = db.query(User).filter(
            (User.phone == receiver_identifier) | (User.email == receiver_identifier)
        ).first()

        if not receiver:
            raise AppException(
                message="Recipient account not found. Please verify the mobile number or email.",
                code="RECIPIENT_NOT_FOUND",
                status_code=404
            )

        if receiver.id == sender.id:
            raise AppException(
                message="You cannot send money to your own wallet account.",
                code="SELF_TRANSFER_NOT_ALLOWED",
                status_code=400
            )

        if receiver.status == UserStatus.SUSPENDED:
            raise AppException(
                message="The recipient account is currently suspended and cannot receive funds.",
                code="RECIPIENT_SUSPENDED",
                status_code=400
            )

        sender_profile = sender.customer_profile
        receiver_profile = receiver.customer_profile
        if not sender_profile or not receiver_profile:
            raise AppException(
                message="Both sender and receiver must have active customer wallet profiles.",
                code="PROFILE_MISSING",
                status_code=400
            )

        # 3. Amount Conversion & Real-Time Risk Score via SecurityAI LightGBM
        amount_dec = Decimal(str(req.amount))
        from backend.app.services.risk_scoring_service import RiskScoringService
        risk_eval = RiskScoringService.evaluate(
            amount=float(amount_dec),
            tx_type="SEND_MONEY",
            sender_profile=sender_profile
        )

        # 4. Check High-Risk Threshold
        if risk_eval.decision == RiskDecision.BLOCK_AND_FLAG:
            ref = generate_transaction_reference()
            blocked_txn = Transaction(
                transaction_reference=ref,
                idempotency_key=req.idempotency_key,
                sender_id=sender.id,
                receiver_id=receiver.id,
                amount=amount_dec,
                fee=Decimal("0.00"),
                transaction_type=TransactionType.SEND_MONEY,
                status=TransactionStatus.BLOCKED,
                category=req.category or "General",
                description="Transaction blocked by SecurityAI Anomaly Detection",
                is_flagged_fraud=True
            )
            db.add(blocked_txn)
            db.flush()

            db.add(RiskScore(
                transaction_id=blocked_txn.id,
                risk_score=Decimal(str(risk_eval.risk_score)),
                risk_level=risk_eval.risk_level,
                decision=risk_eval.decision,
                reasons=json.dumps(risk_eval.reasons),
                inference_latency_ms=Decimal(str(risk_eval.inference_latency_ms))
            ))

            db.add(AuditLog(
                actor_id=sender.id,
                actor_role="CUSTOMER",
                action="SECURITY_HIGH_RISK_BLOCK",
                resource="TRANSACTIONS",
                resource_id=blocked_txn.id,
                details=f'{{"amount": {float(amount_dec)}, "risk_score": {risk_eval.risk_score}, "reasons": {risk_eval.reasons}}}'
            ))
            db.commit()

            raise AppException(
                message=f"Transfer blocked by SecurityAI. Risk score: {risk_eval.risk_score:.2f} (High Risk).",
                code="TRANSACTION_BLOCKED_HIGH_RISK",
                status_code=403,
                details={
                    "risk_score": risk_eval.risk_score,
                    "reasons": risk_eval.reasons,
                    "transaction_reference": ref
                }
            )

        # 5. Balance & Grace Overdraft Check
        current_bal = sender_profile.wallet_balance
        shortfall = amount_dec - current_bal
        applied_grace_amount = 0.0

        if shortfall > 0:
            # Check Grace Eligibility
            max_grace = Decimal("50.00")
            is_reliable = sender_profile.reliability_score >= Decimal("0.70")
            has_no_active_grace = sender_profile.grace_balance == Decimal("0.00")
            grace_eligible = is_reliable and has_no_active_grace and (shortfall <= max_grace)

            if not grace_eligible:
                raise AppException(
                    message=f"Insufficient wallet balance of ৳{float(current_bal):.2f} for transfer of ৳{req.amount:.2f}.",
                    code="INSUFFICIENT_FUNDS",
                    status_code=400,
                    details={
                        "current_balance": float(current_bal),
                        "required_amount": float(amount_dec),
                        "shortfall": float(shortfall),
                        "grace_eligible": False
                    }
                )

            # If user consented to apply grace
            if req.apply_grace_if_needed:
                applied_grace_amount = float(shortfall)
                sender_profile.grace_balance += shortfall
                sender_profile.wallet_balance = Decimal("0.00")
                receiver_profile.wallet_balance += amount_dec
                
                # Create Grace Overdraft Record
                grace_req = GraceOverdraftRequest(
                    customer_id=sender_profile.id,
                    requested_amount=shortfall,
                    status=GraceStatus.APPROVED
                )
                db.add(grace_req)
            else:
                # Offer Grace in error details
                raise AppException(
                    message=f"Insufficient balance (৳{float(current_bal):.2f}). You are eligible for upay Grace (৳{float(shortfall):.2f}).",
                    code="INSUFFICIENT_FUNDS_GRACE_OFFERED",
                    status_code=400,
                    details={
                        "current_balance": float(current_bal),
                        "required_amount": float(amount_dec),
                        "shortfall": float(shortfall),
                        "grace_eligible": True,
                        "max_grace_available": float(max_grace)
                    }
                )
        else:
            # Normal ledger deduction
            sender_profile.wallet_balance -= amount_dec
            receiver_profile.wallet_balance += amount_dec

        # 6. Create Transaction Record (Approved / Medium Risk)
        ref = generate_transaction_reference()
        txn = Transaction(
            transaction_reference=ref,
            idempotency_key=req.idempotency_key,
            sender_id=sender.id,
            receiver_id=receiver.id,
            amount=amount_dec,
            fee=Decimal("5.00"),
            transaction_type=TransactionType.SEND_MONEY,
            status=TransactionStatus.COMPLETED,
            category=req.category or "General",
            description=req.description or "Simulated Peer Transfer"
        )
        db.add(txn)
        db.flush()

        # 7. Attach Real LightGBM Risk Score
        risk = RiskScore(
            transaction_id=txn.id,
            risk_score=Decimal(str(risk_eval.risk_score)),
            risk_level=risk_eval.risk_level,
            decision=risk_eval.decision,
            reasons=json.dumps(risk_eval.reasons),
            inference_latency_ms=Decimal(str(risk_eval.inference_latency_ms))
        )
        db.add(risk)

        # 6. Audit & Notification
        db.add(AuditLog(
            actor_id=sender.id,
            actor_role="CUSTOMER",
            action="SEND_MONEY_COMPLETED",
            resource="TRANSACTIONS",
            resource_id=txn.id,
            details=f'{{"amount": {float(amount_dec)}, "receiver": "{receiver.phone}", "ref": "{ref}"}}'
        ))

        db.add(Notification(
            user_id=receiver.id,
            title="Money Received",
            message=f"You received ৳{float(amount_dec):.2f} from {sender_profile.full_name} ({sender.phone}).",
            notification_type=NotificationType.TRANSACTION_UPDATE
        ))

        db.commit()
        db.refresh(txn)

        return format_transaction_response(txn, applied_grace=applied_grace_amount)

    @staticmethod
    def cash_out(db: Session, customer: User, req: CashOutRequest) -> TransactionResponse:
        """Process customer cash-out at an agent point."""
        if customer.is_frozen:
            raise AppException(
                message="Your account is locked by Master Freeze. Cash-outs are prohibited.",
                code="ACCOUNT_FROZEN",
                status_code=403
            )

        if req.idempotency_key:
            existing = db.query(Transaction).filter(Transaction.idempotency_key == req.idempotency_key).first()
            if existing:
                return format_transaction_response(existing)

        # Find Agent
        agent_id_str = req.agent_identifier.strip()
        agent_profile = db.query(AgentProfile).filter(
            (AgentProfile.agent_code == agent_id_str)
        ).first()

        if not agent_profile:
            # Fallback check by agent user phone
            agent_user = db.query(User).filter(User.phone == agent_id_str, User.role == UserRole.AGENT).first()
            if agent_user and agent_user.agent_profile:
                agent_profile = agent_user.agent_profile

        if not agent_profile:
            raise AppException(
                message="Agent not found with the provided code or mobile number.",
                code="AGENT_NOT_FOUND",
                status_code=404
            )

        customer_profile = customer.customer_profile
        amount_dec = Decimal(str(req.amount))
        fee = Decimal("15.00")  # Standard simulated cash-out fee
        total_deduction = amount_dec + fee

        if customer_profile.wallet_balance < total_deduction:
            raise AppException(
                message=f"Insufficient balance (৳{float(customer_profile.wallet_balance):.2f}) for cash-out of ৳{req.amount:.2f} + fee ৳{float(fee):.2f}.",
                code="INSUFFICIENT_FUNDS",
                status_code=400
            )

        if agent_profile.cash_balance < amount_dec:
            raise AppException(
                message="The selected agent currently has insufficient physical cash for this withdrawal.",
                code="AGENT_CASH_SHORTAGE",
                status_code=400
            )

        # Double-entry ledger update
        customer_profile.wallet_balance -= total_deduction
        agent_profile.cash_balance -= amount_dec
        agent_profile.float_balance += amount_dec
        agent_profile.daily_cash_out_volume += amount_dec

        ref = generate_transaction_reference()
        txn = Transaction(
            transaction_reference=ref,
            idempotency_key=req.idempotency_key,
            sender_id=customer.id,
            receiver_id=agent_profile.user_id,
            agent_id=agent_profile.user_id,
            amount=amount_dec,
            fee=fee,
            transaction_type=TransactionType.CASH_OUT,
            status=TransactionStatus.COMPLETED,
            category="Cash-Out",
            description=f"Cash withdrawal at {agent_profile.store_name}"
        )
        db.add(txn)
        db.flush()

        # Risk Score
        risk = RiskScore(
            transaction_id=txn.id,
            risk_score=Decimal("0.12"),
            risk_level=RiskLevel.LOW,
            decision=RiskDecision.ALLOW,
            reasons='["Verified agent withdrawal point"]',
            inference_latency_ms=Decimal("18.0")
        )
        db.add(risk)

        db.commit()
        db.refresh(txn)

        return format_transaction_response(txn)

    @staticmethod
    def cash_in(db: Session, agent: User, req: CashInRequest) -> TransactionResponse:
        """
        Process agent cash-in to a customer.
        Includes automated upay Grace repayment on subsequent cash-in!
        """
        if req.idempotency_key:
            existing = db.query(Transaction).filter(Transaction.idempotency_key == req.idempotency_key).first()
            if existing:
                return format_transaction_response(existing)

        agent_profile = agent.agent_profile
        if not agent_profile:
            raise AppException("Only authorized agents can perform Cash-In operations.", code="AGENT_PROFILE_REQUIRED", status_code=403)

        customer_phone = req.customer_phone.strip()
        customer_user = db.query(User).filter(User.phone == customer_phone, User.role == UserRole.CUSTOMER).first()
        if not customer_user or not customer_user.customer_profile:
            raise AppException("Customer account not found for this mobile number.", code="CUSTOMER_NOT_FOUND", status_code=404)

        customer_profile = customer_user.customer_profile
        amount_dec = Decimal(str(req.amount))

        if agent_profile.float_balance < amount_dec:
            raise AppException(
                message=f"Agent float balance (৳{float(agent_profile.float_balance):.2f}) is insufficient for this cash-in.",
                code="INSUFFICIENT_FLOAT",
                status_code=400
            )

        # Agent balances
        agent_profile.float_balance -= amount_dec
        agent_profile.cash_balance += amount_dec

        # Grace auto-recovery calculation
        active_grace = customer_profile.grace_balance
        repaid_grace = Decimal("0.00")
        if active_grace > Decimal("0.00"):
            repaid_grace = min(active_grace, amount_dec)
            customer_profile.grace_balance -= repaid_grace
            net_deposit = amount_dec - repaid_grace
            customer_profile.wallet_balance += net_deposit

            # Mark Grace requests as repaid
            pending_requests = db.query(GraceOverdraftRequest).filter(
                GraceOverdraftRequest.customer_id == customer_profile.id,
                GraceOverdraftRequest.status == GraceStatus.APPROVED
            ).all()
            for gr in pending_requests:
                gr.status = GraceStatus.REPAID
                gr.repaid_amount = gr.requested_amount

            # Notify customer of automatic loan recovery
            db.add(Notification(
                user_id=customer_user.id,
                title="upay Grace Repayment",
                message=f"৳{float(repaid_grace):.2f} was recovered towards your active Grace overdraft. Net ৳{float(net_deposit):.2f} credited.",
                notification_type=NotificationType.GRACE_OFFER
            ))
        else:
            customer_profile.wallet_balance += amount_dec

        ref = generate_transaction_reference()
        txn = Transaction(
            transaction_reference=ref,
            idempotency_key=req.idempotency_key,
            sender_id=agent.id,
            receiver_id=customer_user.id,
            agent_id=agent.id,
            amount=amount_dec,
            fee=Decimal("0.00"),
            transaction_type=TransactionType.CASH_IN,
            status=TransactionStatus.COMPLETED,
            category="Cash-In",
            description=f"Cash deposit from {agent_profile.store_name}"
        )
        db.add(txn)
        db.flush()

        risk = RiskScore(
            transaction_id=txn.id,
            risk_score=Decimal("0.02"),
            risk_level=RiskLevel.LOW,
            decision=RiskDecision.ALLOW,
            reasons='["Authorized agent cash deposit"]',
            inference_latency_ms=Decimal("11.5")
        )
        db.add(risk)

        db.commit()
        db.refresh(txn)

        return format_transaction_response(txn)

    @staticmethod
    def get_history(
        db: Session,
        user: User,
        page: int = 1,
        page_size: int = 20,
        tx_type: Optional[TransactionType] = None
    ) -> Dict[str, Any]:
        """Retrieve paginated transaction history with strict role filtering."""
        query = db.query(Transaction)

        if user.role == UserRole.CUSTOMER:
            query = query.filter(or_(Transaction.sender_id == user.id, Transaction.receiver_id == user.id))
        elif user.role == UserRole.AGENT:
            query = query.filter(Transaction.agent_id == user.id)
        # ADMIN / RISK_ANALYST sees all

        if tx_type:
            query = query.filter(Transaction.transaction_type == tx_type)

        total = query.count()
        offset = (page - 1) * page_size
        txns = query.order_by(desc(Transaction.created_at)).offset(offset).limit(page_size).all()

        items = [format_transaction_response(t) for t in txns]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
