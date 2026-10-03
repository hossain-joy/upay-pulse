"""
upay Pulse - CustomerAI: upay Grace Micro-Overdraft Scorer
Explainable credit limit scoring model providing dynamic limits (৳20 - ৳500),
repayment likelihood, and transparent feature attribution reasons.
"""

from typing import Dict, List, Any, Optional

class GraceCreditScorer:
    """
    Evaluates alternative MFS transaction data to generate an explainable
    micro-overdraft credit score and approved limit.
    """

    @classmethod
    def evaluate_credit(
        cls,
        reliability_score: float,       # 0.0 to 1.0 (from customer_profile)
        account_age_days: int,          # account tenure
        avg_monthly_inflow: float,      # monthly cash in / salary
        current_wallet_balance: float,  # current balance
        has_active_grace_debt: bool,    # True if user currently has an outstanding grace loan
        past_repayment_rate: float = 1.0 # 0.0 to 1.0 (ratio of loans repaid on time)
    ) -> Dict[str, Any]:
        """
        Calculates credit score (300-850), approved limit (৳20 - ৳500),
        repayment probability, and explainable positive/negative factors.
        """
        positive_factors = []
        risk_factors = []

        # Disqualifying condition: active unpaid grace loan
        if has_active_grace_debt:
            return {
                "eligible": False,
                "credit_score": 420,
                "approved_limit": 0.0,
                "repayment_likelihood_pct": 25.0,
                "positive_factors": [],
                "risk_factors": ["Active outstanding upay Grace loan pending repayment"],
                "decision": "DECLINED_ACTIVE_LOAN",
                "message": "Please clear your existing upay Grace overdraft before requesting additional funds."
            }

        # Baseline Score: 500
        score = 500.0

        # Factor 1: Reliability Rating (MFS internal history)
        if reliability_score >= 0.85:
            score += 120.0
            positive_factors.append(f"Excellent platform reliability rating ({reliability_score:.0%})")
        elif reliability_score >= 0.70:
            score += 60.0
            positive_factors.append(f"Satisfactory platform reliability rating ({reliability_score:.0%})")
        else:
            score -= 80.0
            risk_factors.append(f"Low platform reliability rating ({reliability_score:.0%})")

        # Factor 2: Account Tenure
        if account_age_days >= 180:
            score += 80.0
            positive_factors.append(f"Established MFS account tenure ({account_age_days} days)")
        elif account_age_days >= 60:
            score += 40.0
            positive_factors.append(f"Active account tenure ({account_age_days} days)")
        else:
            score -= 50.0
            risk_factors.append(f"New account tenure ({account_age_days} days < 60 days)")

        # Factor 3: Monthly Inflow
        if avg_monthly_inflow >= 40000.0:
            score += 90.0
            positive_factors.append(f"Strong monthly cash-flow inflow (৳{avg_monthly_inflow:,.0f})")
        elif avg_monthly_inflow >= 15000.0:
            score += 50.0
            positive_factors.append(f"Consistent monthly cash-flow inflow (৳{avg_monthly_inflow:,.0f})")
        else:
            score -= 40.0
            risk_factors.append(f"Low monthly inflow volume (৳{avg_monthly_inflow:,.0f})")

        # Factor 4: Repayment History
        if past_repayment_rate >= 0.90:
            score += 50.0
            positive_factors.append("Flawless past overdraft auto-recovery record")
        else:
            score -= 70.0
            risk_factors.append(f"Suboptimal past repayment rate ({past_repayment_rate:.0%})")

        # Clamp credit score between 300 and 850
        final_score = int(max(300, min(850, round(score))))
        repayment_prob = round(max(30.0, min(99.0, (final_score - 300) / 5.5)), 1)

        # Dynamic Limit Tier Assignment
        eligible = (final_score >= 600)
        approved_limit = 0.0

        if final_score >= 750:
            approved_limit = 50.0  # Top hackathon tier (up to 50 BDT instant grace)
        elif final_score >= 670:
            approved_limit = 35.0
        elif final_score >= 600:
            approved_limit = 20.0
        else:
            eligible = False
            approved_limit = 0.0

        decision = "APPROVED" if eligible else "DECLINED"
        message = (
            f"Approved for upay Grace emergency overdraft up to ৳{approved_limit:.2f}."
            if eligible else
            "Credit profile does not currently qualify for automatic overdraft."
        )

        return {
            "eligible": eligible,
            "credit_score": final_score,
            "approved_limit": approved_limit,
            "repayment_likelihood_pct": repayment_prob,
            "positive_factors": positive_factors,
            "risk_factors": risk_factors,
            "decision": decision,
            "message": message
        }
