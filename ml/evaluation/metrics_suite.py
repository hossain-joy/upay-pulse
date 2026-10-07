"""
upay Pulse — Comprehensive Fraud ML Evaluation Metrics Suite (Workstream 5)
Calculates:
- PR-AUC (Average Precision) — Primary metric for class-imbalanced fraud detection
- ROC-AUC
- Precision, Recall, F1
- Recall at Fixed False Positive Rates: Recall @ 0.5% FPR, Recall @ 1.0% FPR, Recall @ 2.0% FPR
- Calibration / Brier Score
"""

import numpy as np
from typing import Dict, Any, Tuple
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
    roc_curve,
    confusion_matrix
)

def recall_at_fixed_fpr(y_true: np.ndarray, y_proba: np.ndarray, target_fpr: float = 0.01) -> Tuple[float, float]:
    """
    Computes recall achieved when operating threshold yields <= target_fpr.
    Returns (recall_at_fpr, operational_threshold).
    """
    fpr, tpr, thresholds = roc_curve(y_true, y_proba)
    # Find index where fpr is closest to and <= target_fpr
    valid_indices = np.where(fpr <= target_fpr)[0]
    if len(valid_indices) == 0:
        return 0.0, 1.0
    best_idx = valid_indices[-1]
    return float(tpr[best_idx]), float(thresholds[best_idx])

def evaluate_fraud_model(y_true: np.ndarray, y_proba: np.ndarray, threshold: float = 0.50) -> Dict[str, Any]:
    """
    Computes the full production fraud evaluation matrix.
    """
    y_true = np.asarray(y_true).astype(int)
    y_proba = np.asarray(y_proba).astype(float)
    y_pred = (y_proba >= threshold).astype(int)

    # Core curves
    roc_auc = float(roc_auc_score(y_true, y_proba)) if len(np.unique(y_true)) > 1 else 0.5
    pr_auc = float(average_precision_score(y_true, y_proba)) if len(np.unique(y_true)) > 1 else 0.0

    # Recall at fixed false positive rates
    rec_at_05, thresh_05 = recall_at_fixed_fpr(y_true, y_proba, target_fpr=0.005)
    rec_at_10, thresh_10 = recall_at_fixed_fpr(y_true, y_proba, target_fpr=0.010)
    rec_at_20, thresh_20 = recall_at_fixed_fpr(y_true, y_proba, target_fpr=0.020)

    # Standard metrics at current decision threshold
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    brier = float(brier_score_loss(y_true, y_proba))

    cm = confusion_matrix(y_true, y_pred).tolist()
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
    actual_fpr = fp / max(tn + fp, 1)

    return {
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "recall_at_0_5_pct_fpr": round(rec_at_05, 4),
        "recall_at_1_0_pct_fpr": round(rec_at_10, 4),
        "recall_at_2_0_pct_fpr": round(rec_at_20, 4),
        "threshold_for_1pct_fpr": round(thresh_10, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "brier_score": round(brier, 4),
        "operating_threshold": round(threshold, 2),
        "operating_fpr": round(actual_fpr, 4),
        "confusion_matrix": {
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp
        }
    }
