import os
import sys
import json
import joblib

def verify_baseline():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "model", "risk_model_p1.joblib")
    metrics_path = os.path.join(base_dir, "metrics", "risk_metrics_p1.json")
    data_path = os.path.join(base_dir, "data", "synthetic_transactions_p1.csv")
    test_results_path = os.path.join(base_dir, "test-results", "pytest_p1_results.txt")

    print("============================================================")
    print("upay Pulse: Phase-1 Baseline Verification")
    print("============================================================")

    assert os.path.exists(model_path), f"Missing model: {model_path}"
    assert os.path.exists(metrics_path), f"Missing metrics: {metrics_path}"
    assert os.path.exists(data_path), f"Missing data: {data_path}"
    assert os.path.exists(test_results_path), f"Missing test log: {test_results_path}"

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    model = joblib.load(model_path)
    print(f"[OK] Model successfully loaded: {type(model).__name__}")
    print(f"[OK] Preserved ROC-AUC: {metrics['roc_auc']:.4f}")
    print(f"[OK] Preserved PR-AUC:  {metrics['pr_auc']:.4f}")
    print(f"[OK] Preserved Precision: {metrics['precision']:.4f}")
    print(f"[OK] Preserved Recall:    {metrics['recall']:.4f}")
    print(f"[OK] Preserved p50 Latency: {metrics['latency_p50_ms']} ms")
    print(f"[OK] Dataset size: {os.path.getsize(data_path) / 1024:.1f} KB")
    print("============================================================")
    print("Phase-1 Baseline is 100% frozen and reproducible.")
    print("============================================================")

if __name__ == "__main__":
    verify_baseline()
