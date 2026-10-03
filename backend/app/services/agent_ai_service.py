"""
upay Pulse - AgentAI Service
Forecasts 7-day cash-out demand, detects liquidity stockouts in garment belts,
and executes float-to-cash operational rebalancing.
"""

from typing import Dict, Any, List
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.exceptions import AppException
from backend.app.core.events import event_bus
from backend.app.models.user import User
from backend.app.models.agent import AgentProfile
from backend.app.models.agent_ai import AgentLiquidityForecast
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.audit import AuditLog
from backend.app.schemas.agent_ai import (
    RebalanceRequest,
    AgentLiquidityForecastResponse,
    RebalanceResponse
)
from ml.agent.liquidity_forecaster import AgentLiquidityForecaster

class AgentAIService:

    @classmethod
    def get_forecast(cls, db: Session, user: User) -> Dict[str, Any]:
        """
        Calculates 7-day liquidity projection for an agent terminal.
        """
        profile: AgentProfile = user.agent_profile
        if not profile:
            raise AppException("Agent terminal profile required.", code="AGENT_PROFILE_MISSING", status_code=400)

        cash_bal = float(profile.cash_balance)
        float_bal = float(profile.float_balance)
        base_vol = float(profile.daily_cash_out_volume or (65000.0 if profile.is_factory_zone else 25000.0))

        forecast = AgentLiquidityForecaster.generate_7_day_forecast(
            current_cash_balance=cash_bal,
            current_float_balance=float_bal,
            daily_baseline_volume=base_vol,
            is_factory_zone=profile.is_factory_zone
        )

        # Sync/record forecast entries in database
        today_date = date.today()
        # Delete existing future forecasts for this agent to avoid duplicates
        db.query(AgentLiquidityForecast).filter(
            AgentLiquidityForecast.agent_id == profile.id,
            AgentLiquidityForecast.target_date >= today_date
        ).delete()
        db.flush()

        for pt in forecast["daily_forecast"]:
            target_d = date.fromisoformat(pt["date"])
            db_forecast = AgentLiquidityForecast(
                agent_id=profile.id,
                target_date=target_d,
                hour_of_day=12,
                predicted_cash_out=Decimal(str(pt["predicted_cash_out"])),
                recommended_float=Decimal(str(pt["recommended_float"])),
                surge_flag=pt["surge_flag"],
                surge_reason=pt.get("surge_reason")
            )
            db.add(db_forecast)

        # Proactive Stockout Warning Notification
        if forecast["stockout_risk"] in ("CRITICAL", "ELEVATED"):
            existing_notif = db.query(Notification).filter(
                Notification.user_id == user.id,
                Notification.notification_type == NotificationType.SURGE_WARNING,
                Notification.title == "Liquidity Stockout Alert"
            ).first()

            if not existing_notif:
                db.add(Notification(
                    user_id=user.id,
                    title="Liquidity Stockout Alert",
                    message=forecast["rebalance_suggestion"]["reason"],
                    notification_type=NotificationType.SURGE_WARNING
                ))

        db.commit()

        # Build Response
        return {
            "agent_code": profile.agent_code,
            "store_name": profile.store_name,
            "location_cluster": profile.location_cluster,
            "is_factory_zone": profile.is_factory_zone,
            "current_cash_balance": cash_bal,
            "current_float_balance": float_bal,
            "total_7d_predicted_cash_out": forecast["total_7d_predicted_cash_out"],
            "stockout_risk": forecast["stockout_risk"],
            "days_until_stockout": forecast["days_until_stockout"],
            "rebalance_suggestion": forecast["rebalance_suggestion"],
            "daily_forecast": forecast["daily_forecast"]
        }

    @classmethod
    def rebalance(cls, db: Session, user: User, req: RebalanceRequest) -> Dict[str, Any]:
        """
        Executes simulated liquidity rebalance between physical cash and digital float.
        """
        profile: AgentProfile = user.agent_profile
        if not profile:
            raise AppException("Agent terminal profile required.", code="AGENT_PROFILE_MISSING", status_code=400)

        prev_cash = float(profile.cash_balance)
        prev_float = float(profile.float_balance)
        amt_dec = Decimal(str(req.amount))

        if req.action == "FLOAT_TO_CASH":
            if profile.float_balance < amt_dec:
                raise AppException(
                    message=f"Insufficient digital float (৳{prev_float:,.2f}) for ৳{req.amount:,.2f} conversion.",
                    code="INSUFFICIENT_FLOAT",
                    status_code=400
                )
            profile.float_balance -= amt_dec
            profile.cash_balance += amt_dec
            msg = f"Successfully converted ৳{req.amount:,.2f} float into cash drawer."

        elif req.action == "CASH_TO_FLOAT":
            if profile.cash_balance < amt_dec:
                raise AppException(
                    message=f"Insufficient physical cash (৳{prev_cash:,.2f}) for ৳{req.amount:,.2f} deposit.",
                    code="INSUFFICIENT_CASH",
                    status_code=400
                )
            profile.cash_balance -= amt_dec
            profile.float_balance += amt_dec
            msg = f"Successfully deposited ৳{req.amount:,.2f} cash into digital float."

        else:
            raise AppException("Invalid action. Must be FLOAT_TO_CASH or CASH_TO_FLOAT.", code="INVALID_ACTION", status_code=400)

        new_cash = float(profile.cash_balance)
        new_float = float(profile.float_balance)

        # Audit Log
        db.add(AuditLog(
            actor_id=user.id,
            actor_role="AGENT",
            action="LIQUIDITY_REBALANCED",
            resource="AGENT_TERMINAL",
            resource_id=profile.id,
            details=f'{{"action": "{req.action}", "amount": {req.amount}, "new_cash": {new_cash}, "new_float": {new_float}}}'
        ))

        # Event Bus Dispatch
        event_bus.publish_sync("agent.rebalanced", {
            "agent_code": profile.agent_code,
            "action": req.action,
            "amount": req.amount,
            "new_cash": new_cash,
            "new_float": new_float
        })

        db.commit()

        return {
            "agent_code": profile.agent_code,
            "action": req.action,
            "amount": req.amount,
            "previous_cash": prev_cash,
            "new_cash": new_cash,
            "previous_float": prev_float,
            "new_float": new_float,
            "message": msg
        }
