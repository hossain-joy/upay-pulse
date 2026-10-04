"""
upay Pulse - CustomerAI Service
Coordinates 30-day cash flow trajectories, proactive deficit warnings,
alternative credit scoring for upay Grace micro-overdrafts, and Idle Cash Micro-FDRs.
"""

from typing import Dict, Any, List, Optional
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.exceptions import AppException
from backend.app.core.events import event_bus
from backend.app.models.user import User
from backend.app.models.customer import CustomerProfile
from backend.app.models.customer_ai import (
    CashFlowForecast,
    GraceOverdraftRequest, GraceStatus,
    MicroFDRAccount, FDRStatus
)
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.audit import AuditLog
from backend.app.schemas.customer_ai import (
    GraceRequestCreate,
    GraceRepayRequest,
    FDRCreateRequest
)
from ml.customer.cashflow_forecaster import CashFlowForecaster
from ml.customer.grace_scorer import GraceCreditScorer

class CustomerAIService:

    @classmethod
    def get_trajectory(cls, db: Session, user: User) -> Dict[str, Any]:
        """
        Computes 30-day daily balance trajectory and checks for deficit warnings.
        """
        profile: CustomerProfile = user.customer_profile
        if not profile:
            raise AppException("Customer profile required for cash-flow forecasting.", code="PROFILE_MISSING", status_code=400)

        current_bal = float(profile.wallet_balance or 0.0)
        inflow = float(profile.avg_monthly_inflow or 20000.0)
        outflow = float(profile.avg_monthly_outflow or 18000.0)
        pattern = profile.spending_pattern or "General"

        forecast = CashFlowForecaster.generate_30_day_forecast(
            current_balance=current_bal,
            avg_monthly_inflow=inflow,
            avg_monthly_outflow=outflow,
            spending_pattern=pattern
        )

        # Proactive Deficit Alert Notification (Safe background notification)
        if forecast.get("has_deficit_alert"):
            try:
                alert = forecast["deficit_alert"]
                existing_notif = db.query(Notification).filter(
                    Notification.user_id == user.id,
                    Notification.notification_type == NotificationType.GRACE_OFFER,
                    Notification.title == "CustomerAI Cash-Flow Deficit Warning"
                ).first()

                if not existing_notif:
                    db.add(Notification(
                        user_id=user.id,
                        title="CustomerAI Cash-Flow Deficit Warning",
                        message=alert["recommended_action"],
                        notification_type=NotificationType.GRACE_OFFER
                    ))
                    db.commit()
            except Exception:
                db.rollback()

        return forecast

    @classmethod
    def get_grace_eligibility(cls, db: Session, user: User) -> Dict[str, Any]:
        """
        Calculates explainable credit score and approved micro-overdraft limit.
        """
        profile: CustomerProfile = user.customer_profile
        if not profile:
            raise AppException("Customer profile required for credit assessment.", code="PROFILE_MISSING", status_code=400)

        # Compute account tenure
        account_age = 180
        if user.created_at:
            account_age = max(1, (datetime.now(timezone.utc) - user.created_at).days)

        has_active_debt = (profile.grace_balance > Decimal("0.00"))

        eval_res = GraceCreditScorer.evaluate_credit(
            reliability_score=float(profile.reliability_score),
            account_age_days=account_age,
            avg_monthly_inflow=float(profile.avg_monthly_inflow or 20000.0),
            current_wallet_balance=float(profile.wallet_balance),
            has_active_grace_debt=has_active_debt,
            past_repayment_rate=1.0
        )

        eval_res["current_grace_balance"] = float(profile.grace_balance)
        return eval_res

    @classmethod
    def request_grace_advance(cls, db: Session, user: User, req: GraceRequestCreate) -> GraceOverdraftRequest:
        """
        Customer requests an instant upay Grace micro-loan advance directly into their wallet.
        """
        profile: CustomerProfile = user.customer_profile
        if not profile:
            raise AppException("Customer profile required.", code="PROFILE_MISSING", status_code=400)

        eligibility = cls.get_grace_eligibility(db, user)
        if not eligibility["eligible"]:
            raise AppException(
                message=eligibility["message"],
                code="GRACE_INELIGIBLE",
                status_code=400,
                details=eligibility
            )

        approved_limit = eligibility["approved_limit"]
        if req.requested_amount > approved_limit:
            raise AppException(
                message=f"Requested overdraft of ৳{req.requested_amount:.2f} exceeds your approved limit of ৳{approved_limit:.2f}.",
                code="EXCEEDS_APPROVED_LIMIT",
                status_code=400,
                details={"approved_limit": approved_limit, "requested": req.requested_amount}
            )

        advance_dec = Decimal(str(req.requested_amount))

        # Credit wallet & record grace obligation
        profile.wallet_balance += advance_dec
        profile.grace_balance += advance_dec

        grace_req = GraceOverdraftRequest(
            customer_id=profile.id,
            requested_amount=advance_dec,
            repaid_amount=Decimal("0.00"),
            status=GraceStatus.APPROVED
        )
        db.add(grace_req)

        # Audit & Notification
        db.add(AuditLog(
            actor_id=user.id,
            actor_role="CUSTOMER",
            action="GRACE_OVERDRAFT_ADVANCED",
            resource="WALLET",
            resource_id=profile.id,
            details=f'{{"amount": {float(advance_dec)}, "new_wallet_balance": {float(profile.wallet_balance)}}}'
        ))

        db.add(Notification(
            user_id=user.id,
            title="upay Grace Overdraft Approved",
            message=f"৳{req.requested_amount:.2f} credited to your wallet. Will be automatically settled on your next cash-in.",
            notification_type=NotificationType.TRANSACTION_UPDATE
        ))

        event_bus.publish_sync("customer.grace_advanced", {
            "customer_id": profile.id,
            "amount": float(advance_dec),
            "phone": user.phone
        })

        db.commit()
        db.refresh(grace_req)
        return grace_req

    @classmethod
    def repay_grace_advance(cls, db: Session, user: User, req: Optional[GraceRepayRequest] = None) -> Dict[str, Any]:
        """
        Customer repays their active upay Grace micro-loan advance directly from their wallet balance.
        """
        profile: CustomerProfile = user.customer_profile
        if not profile:
            raise AppException("Customer profile required.", code="PROFILE_MISSING", status_code=400)

        current_debt = Decimal(str(profile.grace_balance or 0.0))
        if current_debt <= Decimal("0.00"):
            raise AppException("You do not have any active upay Grace overdraft to repay.", code="NO_ACTIVE_GRACE", status_code=400)

        # Repay requested amount or full balance
        repay_target = current_debt
        if req and req.repay_amount is not None and req.repay_amount > 0:
            repay_target = min(Decimal(str(req.repay_amount)), current_debt)

        if profile.wallet_balance < repay_target:
            raise AppException(
                message=f"Insufficient wallet balance to repay overdraft. Required: ৳{float(repay_target):.2f}, Available: ৳{float(profile.wallet_balance):.2f}.",
                code="INSUFFICIENT_FUNDS",
                status_code=400
            )

        # Deduct from wallet and reduce grace obligation
        profile.wallet_balance -= repay_target
        profile.grace_balance -= repay_target

        # Update pending/approved grace requests
        grace_requests = db.query(GraceOverdraftRequest).filter(
            GraceOverdraftRequest.customer_id == profile.id,
            GraceOverdraftRequest.status == GraceStatus.APPROVED
        ).order_by(GraceOverdraftRequest.created_at.asc()).all()

        remaining_to_allocate = repay_target
        for gr in grace_requests:
            unpaid = gr.requested_amount - gr.repaid_amount
            if unpaid <= 0:
                gr.status = GraceStatus.REPAID
                continue
            pay_this = min(unpaid, remaining_to_allocate)
            gr.repaid_amount += pay_this
            remaining_to_allocate -= pay_this
            if gr.repaid_amount >= gr.requested_amount:
                gr.status = GraceStatus.REPAID
            if remaining_to_allocate <= Decimal("0.00"):
                break

        # Audit & Notification
        db.add(AuditLog(
            actor_id=user.id,
            actor_role="CUSTOMER",
            action="GRACE_OVERDRAFT_REPAID",
            resource="WALLET",
            resource_id=profile.id,
            details=f'{{"repaid_amount": {float(repay_target)}, "remaining_grace_balance": {float(profile.grace_balance)}, "new_wallet_balance": {float(profile.wallet_balance)}}}'
        ))

        db.add(Notification(
            user_id=user.id,
            title="upay Grace Overdraft Repaid",
            message=f"৳{float(repay_target):.2f} repaid from your wallet. Remaining grace balance: ৳{float(profile.grace_balance):.2f}.",
            notification_type=NotificationType.TRANSACTION_UPDATE
        ))

        event_bus.publish_sync("customer.grace_repaid", {
            "customer_id": profile.id,
            "repaid_amount": float(repay_target),
            "phone": user.phone
        })

        db.commit()

        return {
            "customer_id": profile.id,
            "repaid_amount": float(repay_target),
            "remaining_grace_balance": float(profile.grace_balance),
            "new_wallet_balance": float(profile.wallet_balance),
            "message": f"৳{float(repay_target):.2f} successfully repaid. Your credit limit is restored!"
        }

    @classmethod
    def get_fdr_recommendations(cls, db: Session, user: User) -> Dict[str, Any]:
        """
        Analyzes idle cash and presents high-yield Micro-FDR terms (7d, 30d, 90d).
        """
        profile: CustomerProfile = user.customer_profile
        if not profile:
            raise AppException("Customer profile required.", code="PROFILE_MISSING", status_code=400)

        wallet_bal = float(profile.wallet_balance)
        min_threshold = 200.0
        is_eligible = (wallet_bal >= min_threshold)

        # Suggest locking up to 40% of balance (or min 200 BDT)
        suggested_deposit = round(max(200.0, wallet_bal * 0.40), 2) if is_eligible else 0.0

        terms = [
            (7, 6.50),   # 7 days @ 6.50%
            (30, 7.50),  # 30 days @ 7.50%
            (90, 8.50)   # 90 days @ 8.50%
        ]

        options = []
        for days, rate in terms:
            profit = round(suggested_deposit * (rate / 100.0) * (days / 365.0), 2) if is_eligible else 0.0
            options.append({
                "term_days": days,
                "interest_rate_pct": rate,
                "projected_profit": profit,
                "total_maturity_amount": round(suggested_deposit + profit, 2)
            })

        msg = (
            f"You have ৳{wallet_bal:.2f} available. Earn up to 8.50% p.a. by locking idle funds into a flexible Micro-FDR."
            if is_eligible else
            f"Minimum balance of ৳{min_threshold:.2f} required to open a Micro-FDR."
        )

        return {
            "idle_balance_detected": wallet_bal,
            "recommended_deposit": suggested_deposit,
            "minimum_threshold": min_threshold,
            "is_eligible": is_eligible,
            "options": options,
            "message": msg
        }

    @classmethod
    def create_fdr(cls, db: Session, user: User, req: FDRCreateRequest) -> Dict[str, Any]:
        """
        Locks customer funds into an active Micro-FDR account.
        """
        profile: CustomerProfile = user.customer_profile
        if not profile:
            raise AppException("Customer profile required.", code="PROFILE_MISSING", status_code=400)

        rates_map = {7: 6.50, 30: 7.50, 90: 8.50}
        if req.term_days not in rates_map:
            raise AppException("Supported FDR terms are 7, 30, or 90 days.", code="INVALID_TERM", status_code=400)

        principal_dec = Decimal(str(req.principal_amount))
        if profile.wallet_balance < principal_dec:
            raise AppException(
                message=f"Insufficient wallet balance. You have ৳{float(profile.wallet_balance):.2f}, requested ৳{req.principal_amount:.2f}.",
                code="INSUFFICIENT_FUNDS",
                status_code=400
            )

        # Deduct principal from wallet
        profile.wallet_balance -= principal_dec

        rate = rates_map[req.term_days]
        start_d = date.today()
        maturity_d = start_d + timedelta(days=req.term_days)

        fdr = MicroFDRAccount(
            customer_id=profile.id,
            principal_amount=principal_dec,
            term_days=req.term_days,
            interest_rate_pct=Decimal(str(rate)),
            start_date=start_d,
            maturity_date=maturity_d,
            status=FDRStatus.ACTIVE
        )
        db.add(fdr)

        profit = round(req.principal_amount * (rate / 100.0) * (req.term_days / 365.0), 2)

        # Audit & Notification
        db.add(AuditLog(
            actor_id=user.id,
            actor_role="CUSTOMER",
            action="MICRO_FDR_OPENED",
            resource="MICRO_FDR",
            resource_id=fdr.id,
            details=f'{{"principal": {req.principal_amount}, "term_days": {req.term_days}, "maturity": "{maturity_d}"}}'
        ))

        db.add(Notification(
            user_id=user.id,
            title="Micro-FDR Opened Successfully",
            message=f"৳{req.principal_amount:.2f} locked for {req.term_days} days @ {rate}%. Guaranteed payout on {maturity_d}: ৳{round(req.principal_amount + profit, 2):.2f}.",
            notification_type=NotificationType.FDR_RECOMMENDATION
        ))

        db.commit()
        db.refresh(fdr)

        return {
            "id": fdr.id,
            "customer_id": fdr.customer_id,
            "principal_amount": float(fdr.principal_amount),
            "term_days": int(fdr.term_days),
            "interest_rate_pct": float(fdr.interest_rate_pct),
            "start_date": fdr.start_date,
            "maturity_date": fdr.maturity_date,
            "status": fdr.status,
            "projected_profit": profit,
            "total_at_maturity": round(req.principal_amount + profit, 2)
        }

    @classmethod
    def list_fdrs(cls, db: Session, user: User) -> List[Dict[str, Any]]:
        """
        Lists customer's Micro-FDR accounts with profit calculations.
        """
        profile: CustomerProfile = user.customer_profile
        if not profile:
            return []

        fdrs = db.query(MicroFDRAccount).filter(
            MicroFDRAccount.customer_id == profile.id
        ).order_by(desc(MicroFDRAccount.created_at)).all()

        results = []
        for f in fdrs:
            p = float(f.principal_amount)
            r = float(f.interest_rate_pct)
            t = int(f.term_days)
            profit = round(p * (r / 100.0) * (t / 365.0), 2)
            results.append({
                "id": f.id,
                "customer_id": f.customer_id,
                "principal_amount": p,
                "term_days": t,
                "interest_rate_pct": r,
                "start_date": f.start_date,
                "maturity_date": f.maturity_date,
                "status": f.status.value if hasattr(f.status, 'value') else str(f.status),
                "projected_profit": profit,
                "total_at_maturity": round(p + profit, 2)
            })
        return results

    @classmethod
    def liquidate_fdr(cls, db: Session, user: User, fdr_id: str) -> Dict[str, Any]:
        """
        Liquidate / close an active or matured Micro-FDR account and refund funds to wallet.
        """
        profile: CustomerProfile = user.customer_profile
        if not profile:
            raise AppException("Customer profile required.", code="PROFILE_MISSING", status_code=400)

        fdr = db.query(MicroFDRAccount).filter(
            MicroFDRAccount.id == fdr_id,
            MicroFDRAccount.customer_id == profile.id
        ).first()

        if not fdr:
            raise AppException("Micro-FDR account not found.", code="FDR_NOT_FOUND", status_code=404)

        if fdr.status != FDRStatus.ACTIVE:
            status_str = fdr.status.value if hasattr(fdr.status, 'value') else str(fdr.status)
            raise AppException(f"This Micro-FDR account is already {status_str}.", code="FDR_ALREADY_CLOSED", status_code=400)

        today = date.today()
        is_matured = today >= fdr.maturity_date
        principal = float(fdr.principal_amount)
        rate = float(fdr.interest_rate_pct)
        term_days = int(fdr.term_days)

        full_profit = round(principal * (rate / 100.0) * (term_days / 365.0), 2)
        
        if is_matured:
            profit_payout = full_profit
            fdr.status = FDRStatus.MATURED
            status_msg = "Matured Micro-FDR settled with full profit."
        else:
            days_elapsed = max(1, (today - fdr.start_date).days)
            prorated_profit = round(principal * (rate / 100.0) * (days_elapsed / 365.0) * 0.75, 2)
            profit_payout = prorated_profit
            fdr.status = FDRStatus.PRE_CLOSED
            status_msg = f"Premature withdrawal after {days_elapsed} days. Principal refunded with prorated profit."

        total_payout = principal + profit_payout
        payout_dec = Decimal(str(total_payout))
        profile.wallet_balance += payout_dec

        db.add(AuditLog(
            actor_id=user.id,
            actor_role="CUSTOMER",
            action="MICRO_FDR_LIQUIDATED",
            resource="MICRO_FDR",
            resource_id=fdr.id,
            details=f'{{"principal": {principal}, "profit_paid": {profit_payout}, "total_refunded": {total_payout}, "status": "{fdr.status.value}"}}'
        ))

        db.add(Notification(
            user_id=user.id,
            title="Micro-FDR Funds Returned to Wallet",
            message=f"৳{total_payout:.2f} (৳{principal:.2f} principal + ৳{profit_payout:.2f} profit) credited back to your wallet.",
            notification_type=NotificationType.FDR_RECOMMENDATION
        ))

        db.commit()

        return {
            "id": fdr.id,
            "status": fdr.status.value if hasattr(fdr.status, 'value') else str(fdr.status),
            "principal_amount": principal,
            "profit_paid": profit_payout,
            "total_refunded": total_payout,
            "new_wallet_balance": float(profile.wallet_balance),
            "message": status_msg
        }
