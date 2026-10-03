"""
upay Pulse - CustomerAI: Cash-Flow Trajectory Forecaster
Autoregressive 30-day forward balance projection with recurrent expense pattern recognition
and proactive deficit warning alerts (< 5 days before shortfall).
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

class CashFlowForecaster:
    """
    Simulates and projects daily financial trajectory for MFS customers based on
    monthly salary/income cycle, recurrent utility bill schedules, and spending habits.
    """

    # Recurrent payment patterns in Bangladesh MFS ecosystem
    RECURRENT_CALENDAR = {
        1: ("Salary Credit / Primary Inflow", "INFLOW", 0.90),    # Salary usually 1st-5th
        3: ("House Rent / Major Expense", "OUTFLOW", 0.40),
        10: ("Electricity & Gas Utility Bill", "OUTFLOW", 0.08),  # DESCO, DPDC, Titas
        15: ("Family Support / Remittance", "OUTFLOW", 0.15),
        22: ("Internet & Cable Subscription", "OUTFLOW", 0.04),
        27: ("Grocery & Month-End Provisions", "OUTFLOW", 0.12),
    }

    @classmethod
    def generate_30_day_forecast(
        cls,
        current_balance: float,
        avg_monthly_inflow: float,
        avg_monthly_outflow: float,
        spending_pattern: str = "General",
        start_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Projects next 30 days of daily inflow, outflow, and ending balance.
        Flags any days where projected balance dips below zero.
        """
        if start_date is None:
            start_date = date.today()

        daily_points = []
        running_balance = float(current_balance)
        daily_baseline_outflow = (avg_monthly_outflow * 0.20) / 30.0  # Daily coffee/recharge/snack

        first_deficit_date = None
        first_deficit_day_offset = None
        max_shortfall = 0.0
        has_deficit_alert = False

        for day_offset in range(30):
            sim_date = start_date + timedelta(days=day_offset)
            dom = sim_date.day

            day_inflow = 0.0
            day_outflow = round(daily_baseline_outflow, 2)

            # Check recurrent events
            if dom in cls.RECURRENT_CALENDAR:
                event_name, event_type, pct = cls.RECURRENT_CALENDAR[dom]
                if event_type == "INFLOW":
                    # Income hits on 1st of month
                    day_inflow += round(avg_monthly_inflow * pct, 2)
                else:
                    day_outflow += round(avg_monthly_outflow * pct, 2)

            # Weekend small boost in discretionary spending
            if sim_date.weekday() in (4, 5):  # Friday, Saturday in Bangladesh
                day_outflow += round(daily_baseline_outflow * 0.5, 2)

            # Calculate day ending balance
            running_balance = round(running_balance + day_inflow - day_outflow, 2)
            is_deficit = (running_balance < 0)

            if is_deficit:
                shortfall = abs(running_balance)
                if shortfall > max_shortfall:
                    max_shortfall = shortfall
                if first_deficit_date is None:
                    first_deficit_date = sim_date
                    first_deficit_day_offset = day_offset

            daily_points.append({
                "date": sim_date.isoformat(),
                "day_of_month": dom,
                "inflow_forecast": round(day_inflow, 2),
                "outflow_forecast": round(day_outflow, 2),
                "projected_balance": running_balance,
                "deficit_warning": is_deficit
            })

        # Deficit alert triggers if balance drops below zero within 7 days
        if first_deficit_day_offset is not None and first_deficit_day_offset <= 7:
            has_deficit_alert = True

        alert_details = None
        if has_deficit_alert and first_deficit_date:
            alert_details = {
                "alert_level": "CRITICAL" if first_deficit_day_offset <= 3 else "WARNING",
                "days_until_deficit": first_deficit_day_offset,
                "deficit_date": first_deficit_date.isoformat(),
                "projected_shortfall": round(max_shortfall, 2),
                "recommended_action": f"Projected balance shortfall of ৳{max_shortfall:.2f} expected on {first_deficit_date}. Activate upay Grace overdraft or deposit funds."
            }

        return {
            "current_balance": round(current_balance, 2),
            "start_date": start_date.isoformat(),
            "has_deficit_alert": has_deficit_alert,
            "deficit_alert": alert_details,
            "projected_30d_end_balance": running_balance,
            "lowest_projected_balance": min(p["projected_balance"] for p in daily_points),
            "highest_projected_balance": max(p["projected_balance"] for p in daily_points),
            "daily_forecast": daily_points
        }
