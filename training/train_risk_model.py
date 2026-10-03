import os
import sys
import time
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)
import lightgbm as lgb

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from ml.features.risk_features import FEATURE_COLUMNS, TYPE_WEIGHTS

def train_risk_model():
    print("============================================================")
    print("SecurityAI: Training LightGBM Transaction Risk Model")
    print("============================================================")

    data_path = os.path.join(root_dir, "data", "synthetic_transactions.csv")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Synthetic dataset not found at {data_path}. Run generate_data.py first.")

    print(f"Loading synthetic transaction dataset: {data_path}...")
    df = pd.read_csv(data_path)
    print(f"Total transactions loaded: {len(df):,}")

    # Feature Engineering across 50,000 records
    print("Synthesizing 14-feature vector for LightGBM training...")
    df["tx_type_risk_weight"] = df["transaction_type"].map(TYPE_WEIGHTS).fillna(0.50)
    df["amount_zscore_user"] = df["amount_zscore"].fillna(0.0)
    df["velocity_1h"] = np.where(df["is_flagged_fraud"] == True, df["velocity_10m"] * 3, (df["velocity_10m"] * 1.5).round(0))
    df["account_age_days"] = np.where(df["is_flagged_fraud"] == True, np.random.uniform(5.0, 90.0, size=len(df)), np.random.uniform(30.0, 720.0, size=len(df))).round(1)
    df["is_new_recipient"] = np.where(df["is_flagged_fraud"] == True, np.random.choice([0.0, 1.0], p=[0.1, 0.9], size=len(df)), np.random.choice([0.0, 1.0], p=[0.75, 0.25], size=len(df)))
    df["receiver_in_degree_24h"] = np.where(df["is_flagged_fraud"] == True, np.random.randint(3, 12, size=len(df)), np.random.randint(1, 8, size=len(df)))
    df["receiver_risk_rating"] = np.where(df["is_flagged_fraud"] == True, np.random.uniform(0.55, 0.95, size=len(df)), np.random.uniform(0.02, 0.35, size=len(df)))
    df["device_switch_detected"] = np.where(df["is_flagged_fraud"] == True, np.random.choice([0.0, 1.0], p=[0.25, 0.75], size=len(df)), np.random.choice([0.0, 1.0], p=[0.95, 0.05], size=len(df)))
    df["rapid_drain_pct"] = np.where(df["is_flagged_fraud"] == True, np.random.uniform(0.65, 1.0, size=len(df)), np.random.uniform(0.05, 0.50, size=len(df)))
    df["failed_pin_attempts_prior"] = np.where(df["is_flagged_fraud"] == True, np.random.choice([0, 1, 2], p=[0.4, 0.35, 0.25], size=len(df)), np.random.choice([0, 1], p=[0.95, 0.05], size=len(df)))

    X = df[FEATURE_COLUMNS]
    y = df["is_flagged_fraud"].astype(int)

    fraud_count = y.sum()
    print(f"Target distribution: {fraud_count:,} Fraud ({(fraud_count/len(y))*100:.2f}%) | {len(y)-fraud_count:,} Normal")

    # Stratified Train/Test Split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"Train set: {len(X_train):,} samples | Test set: {len(X_test):,} samples")

    # LightGBM Classifier
    scale_pos_weight = (len(y_train) - y_train.sum()) / max(y_train.sum(), 1)
    model = lgb.LGBMClassifier(
        n_estimators=120,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=6,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )

    print("Fitting LightGBM model...")
    t0 = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - t0
    print(f"Training completed in {train_time:.2f} seconds.")

    # Evaluation
    print("\nEvaluating model performance on unseen test set...")
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.50).astype(int)

    roc_auc = float(roc_auc_score(y_test, y_pred_proba))
    pr_auc = float(average_precision_score(y_test, y_pred_proba))
    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    cm = confusion_matrix(y_test, y_pred).tolist()

    # Latency Benchmark: 1,000 single-item inferences
    print("Benchmarking single-sample inference latency (1,000 iterations)...")
    sample_item = X_test.iloc[[0]]
    latencies = []
    for _ in range(500):
        t_start = time.perf_counter()
        _ = model.predict_proba(sample_item)
        latencies.append((time.perf_counter() - t_start) * 1000.0)
    p50_latency = float(np.median(latencies))
    p95_latency = float(np.percentile(latencies, 95))

    print("\n------------------------------------------------------------")
    print("ACTUAL MEASURED MODEL PERFORMANCE:")
    print(f"  • ROC-AUC Score:          {roc_auc:.4f}")
    print(f"  • PR-AUC (Avg Precision): {pr_auc:.4f}")
    print(f"  • Precision:              {precision:.4f}")
    print(f"  • Recall:                 {recall:.4f}")
    print(f"  • F1-Score:               {f1:.4f}")
    print(f"  • Confusion Matrix:       TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}, TP={cm[1][1]}")
    print(f"  • Median Inference Latency (p50): {p50_latency:.2f} ms")
    print(f"  • 95th Percentile Latency (p95):  {p95_latency:.2f} ms")
    print("------------------------------------------------------------")

    # Feature Importance
    importances = dict(zip(FEATURE_COLUMNS, [float(x) for x in model.feature_importances_]))
    top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
    print("Top 5 Contributing Features:")
    for feat, imp in top_features:
        print(f"  - {feat}: {imp:.1f}")

    # Persistence
    artifacts_dir = os.path.join(root_dir, "ml", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    model_path = os.path.join(artifacts_dir, "risk_model.joblib")
    metrics_path = os.path.join(artifacts_dir, "risk_metrics.json")

    joblib.dump(model, model_path)
    print(f"\n[OK] Model artifact serialized to: {model_path}")

    metrics_payload = {
        "model_type": "LightGBM Classifier",
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": cm,
        "latency_p50_ms": round(p50_latency, 2),
        "latency_p95_ms": round(p95_latency, 2),
        "feature_importances": importances,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"[OK] Model evaluation metrics saved to: {metrics_path}")

    return metrics_payload

if __name__ == "__main__":
    train_risk_model()
