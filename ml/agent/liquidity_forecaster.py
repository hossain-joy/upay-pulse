"""
upay Pulse - AgentAI: Liquidity Forecaster & Cash-Out Demand Predictor
Predicts 7-day cash-out demand spikes based on Bangladesh factory zone pay cycles,
weekend surges, and recommends proactive float-to-cash rebalancing.
"""

from typing import Dict, List, Any, Optional
from datetime import date, timedelta
from decimal import Decimal

class AgentLiquidityForecaster:
    """
    Forecasting model for MFS agent terminals.
    Predicts daily cash-out volume and detects physical cash depletion risks.
    """

    WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    @classmethod
    def generate_7_day_forecast(
        cls,
        current_cash_balance: float,
        current_float_balance: float,
        daily_baseline_volume: float,
        is_factory_zone: bool,
        start_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Projects next 7 days of cash-out volume, evaluates stockout probability,
        and generates actionable float/cash rebalancing instructions.
        """
        if start_date is None:
            start_date = date.today()

        daily_points = []
        cumulative_cash_out = 0.0
        running_cash = float(current_cash_balance)
        days_until_stockout = None

        total_predicted = 0.0

        for day_offset in range(7):
            sim_date = start_date + timedelta(days=day_offset)
            dom = sim_date.day
            weekday = sim_date.weekday()
            weekday_name = cls.WEEKDAY_NAMES[weekday]

            # Base volume multiplier
            multiplier = 1.0
            surge_flag = False
            surge_reason = None

            # Factor 1: Salary Week (1st - 7th of the month)
            # In garment/factory zones, salary week triggers massive 2.5x - 3.8x cash-outs
            if 1 <= dom <= 7:
                surge_flag = True
                if is_factory_zone:
                    multiplier *= 3.2
                    surge_reason = f"Garment Factory Worker Monthly Wage Disbursement Peak (Day {dom})"
                else:
                    multiplier *= 1.8
                    surge_reason = f"Corporate & Retail Salary Cash-Out Peak (Day {dom})"

            # Factor 2: Weekend Evening Surge (Friday/Saturday)
            if weekday in (4, 5):  # Friday or Saturday
                multiplier *= 1.35
                if not surge_reason:
                    surge_flag = True
                    surge_reason = "Weekend High-Frequency Remittance & Bazaar Shopping"

            # Factor 3: Mid-Month Family Support Peak (14th - 16th)
            elif 14 <= dom <= 16:
                multiplier *= 1.25
                if not surge_reason:
                    surge_flag = True
                    surge_reason = "Mid-Month Village Remittance Demand"

            # Calculate daily predicted cash-out
            predicted_volume = round(daily_baseline_volume * multiplier, 2)
            # Recommended float is typically 1.2x of predicted cash-out to absorb digital inflows
            recommended_float = round(predicted_volume * 1.25, 2)

            total_predicted += predicted_volume
            cumulative_cash_out += predicted_volume

            # Check if physical cash runs out
            if running_cash < predicted_volume and days_until_stockout is None:
                days_until_stockout = day_offset

            running_cash = max(0.0, running_cash - predicted_volume)

            daily_points.append({
                "date": sim_date.isoformat(),
                "day_of_week": weekday_name,
                "predicted_cash_out": predicted_volume,
                "recommended_float": recommended_float,
                "surge_flag": surge_flag,
                "surge_reason": surge_reason
            })

        # Evaluate Stockout Risk
        # 48-hour cash requirements
        next_48h_need = sum(p["predicted_cash_out"] for p in daily_points[:2])
        cash_ratio = (current_cash_balance / next_48h_need) if next_48h_need > 0 else 1.0

        if cash_ratio < 0.60:
            stockout_risk = "CRITICAL"
        elif cash_ratio < 1.0:
            stockout_risk = "ELEVATED"
        elif cash_ratio < 1.4:
            stockout_risk = "MODERATE"
        else:
            stockout_risk = "LOW"

        # Rebalancing Recommendation
        rebalance_action = "OPTIMAL"
        rebalance_amount = 0.0
        rebalance_text = "Your cash-to-float ratio is well balanced for projected demand."

        if current_cash_balance < next_48h_need:
            rebalance_action = "CONVERT_FLOAT_TO_CASH"
            rebalance_amount = round(next_48h_need - current_cash_balance + (next_48h_need * 0.20), 2)
            rebalance_text = (
                f"High cash-out surge expected! Rebalance ৳{rebalance_amount:,.2f} from digital float "
                f"into physical cash drawer before tomorrow morning to prevent customer stockouts."
            )
        elif current_cash_balance > (total_predicted * 1.5) and current_float_balance < (total_predicted * 0.5):
            rebalance_action = "CONVERT_CASH_TO_FLOAT"
            rebalance_amount = round(current_cash_balance - total_predicted, 2)
            rebalance_text = (
                f"Excess physical cash held. Deposit ৳{rebalance_amount:,.2f} cash into digital float "
                f"to maintain inbound cash-in capacity."
            )

        return {
            "current_cash_balance": round(current_cash_balance, 2),
            "current_float_balance": round(current_float_balance, 2),
            "total_7d_predicted_cash_out": round(total_predicted, 2),
            "stockout_risk": stockout_risk,
            "days_until_stockout": days_until_stockout,
            "rebalance_suggestion": {
                "action": rebalance_action,
                "recommended_amount": rebalance_amount,
                "reason": rebalance_text
            },
            "daily_forecast": daily_points
        }
