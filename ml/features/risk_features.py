from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List
import numpy as np

# Transaction type weights
TYPE_WEIGHTS = {
    "CASH_OUT": 0.85,
    "SEND_MONEY": 0.50,
    "MERCHANT_PAY": 0.25,
    "BILL_PAY": 0.15,
    "RECHARGE": 0.05,
    "CASH_IN": 0.10
}

FEATURE_COLUMNS = [
    "amount",
    "amount_zscore_user",
    "velocity_10m",
    "velocity_1h",
    "hour_of_day",
    "is_night_time",
    "account_age_days",
    "is_new_recipient",
    "receiver_in_degree_24h",
    "receiver_risk_rating",
    "device_switch_detected",
    "rapid_drain_pct",
    "failed_pin_attempts_prior",
    "tx_type_risk_weight"
]

class RiskFeatureExtractor:
    """Extracts 14 behavioral and contextual features from a transaction candidate."""

    @staticmethod
    def extract_features(
        amount: float,
        tx_type: str,
        sender_profile: Any = None,
        velocity_10m: int = 1,
        velocity_1h: int = 1,
        is_new_recipient: bool = False,
        receiver_in_degree: int = 1,
        receiver_risk_rating: float = 0.10,
        device_switch: bool = False,
        failed_pin_attempts: int = 0,
        tx_time: datetime = None
    ) -> Dict[str, float]:
        if tx_time is None:
            tx_time = datetime.now(timezone.utc)

        hour = tx_time.hour
        is_night = 1.0 if (1 <= hour <= 5) else 0.0

        # Mean and std estimation from profile
        user_mean = float(sender_profile.avg_monthly_outflow) / 30.0 if sender_profile else 800.0
        user_std = max(user_mean * 0.6, 200.0)
        zscore = (amount - user_mean) / user_std

        # Rapid drain percentage
        wallet_bal = float(sender_profile.wallet_balance) if sender_profile else amount
        rapid_drain = min(1.0, amount / max(wallet_bal, 1.0))

        # Account age
        account_age = 180.0  # default 6 months
        if sender_profile and hasattr(sender_profile, "created_at") and sender_profile.created_at:
            account_age = max(1.0, (tx_time - sender_profile.created_at).total_seconds() / 86400.0)

        tx_weight = TYPE_WEIGHTS.get(tx_type, 0.50)

        return {
            "amount": float(amount),
            "amount_zscore_user": float(round(zscore, 3)),
            "velocity_10m": float(velocity_10m),
            "velocity_1h": float(velocity_1h),
            "hour_of_day": float(hour),
            "is_night_time": float(is_night),
            "account_age_days": float(round(account_age, 1)),
            "is_new_recipient": 1.0 if is_new_recipient else 0.0,
            "receiver_in_degree_24h": float(receiver_in_degree),
            "receiver_risk_rating": float(receiver_risk_rating),
            "device_switch_detected": 1.0 if device_switch else 0.0,
            "rapid_drain_pct": float(round(rapid_drain, 3)),
            "failed_pin_attempts_prior": float(failed_pin_attempts),
            "tx_type_risk_weight": float(tx_weight)
        }

    @staticmethod
    def to_feature_vector(features: Dict[str, float]) -> List[float]:
        return [features[col] for col in FEATURE_COLUMNS]
