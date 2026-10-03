import os
import time
import json
import joblib
import numpy as np
from typing import Dict, Any, List, Optional
from decimal import Decimal
import pandas as pd

from backend.app.core.config import settings
from backend.app.models.risk import RiskLevel, RiskDecision
from backend.app.schemas.risk import RiskEvaluationResponse, RiskMetricsResponse
from ml.features.risk_features import RiskFeatureExtractor, FEATURE_COLUMNS

class RiskScoringService:
    _model = None
    _metrics = None

    @classmethod
    def get_model(cls):
        """Lazy load serialized LightGBM model."""
        if cls._model is None:
            model_path = os.path.join(settings.PROJECT_NAME.lower().replace(" ", "_"), "..", "ml", "artifacts", "risk_model.joblib")
            # Try absolute path from project root
            alt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "artifacts", "risk_model.joblib"))
            target_path = alt_path if os.path.exists(alt_path) else model_path

            if os.path.exists(target_path):
                try:
                    cls._model = joblib.load(target_path)
                except Exception as e:
                    cls._model = None
        return cls._model

    @classmethod
    def evaluate(
        cls,
        amount: float,
        tx_type: str,
        sender_profile: Any = None,
        velocity_10m: int = 1,
        velocity_1h: int = 1,
        is_new_recipient: bool = False,
        receiver_in_degree: int = 1,
        receiver_risk_rating: float = 0.10,
        device_switch: bool = False,
        failed_pin_attempts: int = 0
    ) -> RiskEvaluationResponse:
        """Evaluate real-time transaction risk with LightGBM inference."""
        model = cls.get_model()
        t_start = time.perf_counter()

        # 1. Extract 14 features
        features = RiskFeatureExtractor.extract_features(
            amount=amount,
            tx_type=tx_type,
            sender_profile=sender_profile,
            velocity_10m=velocity_10m,
            velocity_1h=velocity_1h,
            is_new_recipient=is_new_recipient,
            receiver_in_degree=receiver_in_degree,
            receiver_risk_rating=receiver_risk_rating,
            device_switch=device_switch,
            failed_pin_attempts=failed_pin_attempts
        )
        if model is not None:
            feature_df = pd.DataFrame([features])[FEATURE_COLUMNS]
            proba = float(model.predict_proba(feature_df)[0][1])
            risk_score = round(max(0.01, min(0.99, proba)), 3)
        else:
            # Fallback heuristic calculation if model artifact is building
            base = 0.05
            if features["is_night_time"] == 1.0:
                base += 0.25
            if features["amount_zscore_user"] > 2.5:
                base += 0.35
            if features["receiver_risk_rating"] > 0.60:
                base += 0.30
            risk_score = round(min(0.99, base), 3)

        # 2. Decision Logic based on Configurable Thresholds
        if risk_score < settings.RISK_THRESHOLD_LOW:
            risk_level = RiskLevel.LOW
            decision = RiskDecision.ALLOW
        elif risk_score < settings.RISK_THRESHOLD_HIGH:
            risk_level = RiskLevel.MEDIUM
            decision = RiskDecision.FRICTION_CHALLENGE
        else:
            risk_level = RiskLevel.HIGH
            decision = RiskDecision.BLOCK_AND_FLAG

        # 3. Generate Human-Understandable Explainability Reasons
        reasons = []
        if features["amount_zscore_user"] > 2.0:
            reasons.append(f"Transfer amount (৳{amount:,.2f}) is significantly higher than 30-day baseline.")
        if features["is_night_time"] == 1.0:
            reasons.append("Unusual late-night transaction window (01:00 AM - 05:30 AM).")
        if features["receiver_risk_rating"] > 0.50:
            reasons.append("Recipient account has prior suspicious fraud cluster associations.")
        if features["velocity_10m"] > 3:
            reasons.append("High transaction velocity detected in past 10 minutes.")
        if features["device_switch_detected"] == 1.0:
            reasons.append("Transaction initiated from a newly recognized client device.")

        if not reasons:
            reasons.append("Standard behavioral transaction pattern within historical thresholds.")

        latency_ms = (time.perf_counter() - t_start) * 1000.0

        return RiskEvaluationResponse(
            risk_score=risk_score,
            risk_level=risk_level,
            decision=decision,
            reasons=reasons,
            inference_latency_ms=round(latency_ms, 2),
            features=features
        )

    @classmethod
    def get_metrics(cls) -> Optional[Dict[str, Any]]:
        """Retrieve actual measured model evaluation metrics from disk."""
        metrics_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "artifacts", "risk_metrics.json"))
        if os.path.exists(metrics_path):
            with open(metrics_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
