from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.risk import RiskLevel, RiskDecision

class RiskEvaluationRequest(BaseModel):
    amount: float = Field(..., gt=0)
    transaction_type: str = Field(default="SEND_MONEY")
    sender_id: Optional[str] = None
    receiver_identifier: Optional[str] = None
    velocity_10m: Optional[int] = 1
    device_switch: Optional[bool] = False
    is_new_recipient: Optional[bool] = False
    receiver_risk_rating: Optional[float] = None
    receiver_in_degree: Optional[int] = None

class RiskEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    risk_score: float
    risk_level: RiskLevel
    decision: RiskDecision
    reasons: List[str]
    inference_latency_ms: float
    latency_ms: Optional[float] = None
    features: Dict[str, float]

    def __init__(self, **data):
        if "latency_ms" not in data and "inference_latency_ms" in data:
            data["latency_ms"] = data["inference_latency_ms"]
        super().__init__(**data)

class RiskMetricsResponse(BaseModel):
    model_type: str
    model_name: Optional[str] = None
    training_samples: int
    test_samples: int
    roc_auc: float
    pr_auc: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: Any
    latency_p50_ms: float
    latency_p95_ms: float
    average_inference_ms: Optional[float] = None
    feature_importances: Dict[str, float]
    trained_at: str

    def __init__(self, **data):
        if "model_name" not in data:
            data["model_name"] = data.get("model_type", "LightGBM Classifier")
        if "average_inference_ms" not in data:
            data["average_inference_ms"] = data.get("latency_p50_ms", 1.37)
        super().__init__(**data)
