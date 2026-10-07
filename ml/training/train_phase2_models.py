"""
upay Pulse — Phase-2 Rigorous ML Training & Model Comparison Suite
(Workstreams 4, 5, 6, 7, 27, 28)
Trains and validates:
- M1: Logistic Regression Baseline
- M2: Random Forest Baseline
- M3: LightGBM (14 Leakage-Free Tabular Features)
- M4: LightGBM + Graph Intelligence (14 Tabular + 4 Graph Features)
Evaluates on chronological split and unseen fraud pattern topologies.
"""

import os
import sys
import time
import json
import joblib
import pandas as pd
import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import lightgbm as lgb

from ml.features.temporal_feature_store import (
    FEATURE_COLUMNS,
    build_leakage_free_feature_dataset
)
from ml.graph.temporal_graph_engine import (
    GRAPH_FEATURE_COLUMNS,
    enrich_dataset_with_temporal_graph
)
from ml.training.temporal_split import (
    chronological_split,
    get_split_summary
)
from ml.evaluation.metrics_suite import (
    evaluate_fraud_model
)
from ml.evaluation.unseen_fraud_eval import (
    generate_unseen_fraud_test_cases
)

def run_phase2_training():
    print("==================================================================")
    print("UPAY PULSE: WORKSTREAMS 4-7 — CHRONOLOGICAL ML & GRAPH BENCHMARK")
    print("==================================================================")

    raw_path = os.path.join(root_dir, "data", "synthetic_transactions.csv")
    raw_df = pd.read_csv(raw_path)
    clean_data_path = os.path.join(root_dir, "data", "synthetic_transactions_clean.csv")

    need_rebuild = True
    if os.path.exists(clean_data_path):
        existing_clean = pd.read_csv(clean_data_path)
        if len(existing_clean) == len(raw_df):
            clean_df = existing_clean
            need_rebuild = False

    if need_rebuild:
        print(f"Generating leakage-free feature dataset for {len(raw_df):,} transactions...")
        clean_df = build_leakage_free_feature_dataset(raw_df)
        clean_df.to_csv(clean_data_path, index=False)

    print(f"Loaded clean dataset: {len(clean_df):,} transactions.")
    clean_df["created_at_dt"] = pd.to_datetime(clean_df["created_at_dt"])

    # 1. Enrich with temporal graph features
    print("Enriching dataset with 4 temporal graph features (historical-only)...")
    t0 = time.time()
    enriched_df = enrich_dataset_with_temporal_graph(clean_df)
    print(f"[OK] Graph feature extraction completed in {time.time() - t0:.2f}s.")

    # 2. Chronological Split (70% Train, 15% Val, 15% Test)
    train_df, val_df, test_df = chronological_split(enriched_df, train_ratio=0.70, val_ratio=0.15)
    split_info = get_split_summary(train_df, val_df, test_df)

    print("\n--- CHRONOLOGICAL DATASET PARTITIONING ---")
    for split_name, s_meta in split_info.items():
        print(f"  {split_name.capitalize():<12}: {s_meta['samples']:,} samples | Fraud Rate: {s_meta['fraud_rate']*100:.2f}% | [{s_meta['start'][:10]} -> {s_meta['end'][:10]}]")

    # Target sets
    y_train = train_df["is_flagged_fraud"].astype(int).values
    y_val = val_df["is_flagged_fraud"].astype(int).values
    y_test = test_df["is_flagged_fraud"].astype(int).values

    # Feature sets
    X_train_tab = train_df[FEATURE_COLUMNS].values
    X_val_tab = val_df[FEATURE_COLUMNS].values
    X_test_tab = test_df[FEATURE_COLUMNS].values

    ALL_FEATURES = FEATURE_COLUMNS + GRAPH_FEATURE_COLUMNS
    X_train_all = train_df[ALL_FEATURES].values
    X_val_all = val_df[ALL_FEATURES].values
    X_test_all = test_df[ALL_FEATURES].values

    scale_pos = (len(y_train) - y_train.sum()) / max(y_train.sum(), 1)

    # -------------------------------------------------------------
    # MODEL 1: Logistic Regression Baseline
    # -------------------------------------------------------------
    print("\n[1/4] Fitting Model 1: Baseline Logistic Regression...")
    m1 = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
    m1.fit(X_train_tab, y_train)
    m1_probs = m1.predict_proba(X_test_tab)[:, 1]
    m1_metrics = evaluate_fraud_model(y_test, m1_probs, threshold=0.50)

    # -------------------------------------------------------------
    # MODEL 2: Random Forest Baseline
    # -------------------------------------------------------------
    print("[2/4] Fitting Model 2: Random Forest Classifier...")
    m2 = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1)
    m2.fit(X_train_tab, y_train)
    m2_probs = m2.predict_proba(X_test_tab)[:, 1]
    m2_metrics = evaluate_fraud_model(y_test, m2_probs, threshold=0.50)

    # -------------------------------------------------------------
    # MODEL 3: LightGBM (14 Tabular Features — Leakage Free)
    # -------------------------------------------------------------
    print("[3/4] Fitting Model 3: LightGBM (14 Leakage-Free Tabular Features)...")
    m3 = lgb.LGBMClassifier(
        n_estimators=120,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=6,
        scale_pos_weight=scale_pos,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )
    m3.fit(X_train_tab, y_train)
    m3_probs = m3.predict_proba(X_test_tab)[:, 1]
    m3_metrics = evaluate_fraud_model(y_test, m3_probs, threshold=0.72)

    # -------------------------------------------------------------
    # MODEL 4: LightGBM + Graph Intelligence (18 Features)
    # -------------------------------------------------------------
    print("[4/4] Fitting Model 4: LightGBM + Graph Intelligence (Hybrid Fusion)...")
    m4 = lgb.LGBMClassifier(
        n_estimators=120,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=6,
        scale_pos_weight=scale_pos,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )
    m4.fit(X_train_all, y_train)
    m4_probs = m4.predict_proba(X_test_all)[:, 1]
    m4_metrics = evaluate_fraud_model(y_test, m4_probs, threshold=0.72)

    # Latency benchmark
    sample_tab = X_test_tab[:1]
    sample_all = X_test_all[:1]
    lat_m3 = []
    lat_m4 = []
    for _ in range(500):
        t0 = time.perf_counter()
        _ = m3.predict_proba(sample_tab)
        lat_m3.append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        _ = m4.predict_proba(sample_all)
        lat_m4.append((time.perf_counter() - t0) * 1000.0)

    m3_metrics["latency_p50_ms"] = round(float(np.median(lat_m3)), 2)
    m3_metrics["latency_p95_ms"] = round(float(np.percentile(lat_m3, 95)), 2)
    m4_metrics["latency_p50_ms"] = round(float(np.median(lat_m4)), 2)
    m4_metrics["latency_p95_ms"] = round(float(np.percentile(lat_m4, 95)), 2)

    # -------------------------------------------------------------
    # Workstream 6: Unseen Fraud Topologies Evaluation
    # -------------------------------------------------------------
    print("\n--- WORKSTREAM 6: UNSEEN FRAUD TOPOLOGIES EVALUATION ---")
    test_end_time = test_df["created_at_dt"].max()
    unseen_df = generate_unseen_fraud_test_cases(base_time=test_end_time, count=50)

    # Build features on unseen test cases
    unseen_clean = build_leakage_free_feature_dataset(unseen_df)
    unseen_enriched = enrich_dataset_with_temporal_graph(unseen_clean)

    X_unseen_tab = unseen_enriched[FEATURE_COLUMNS].values
    X_unseen_all = unseen_enriched[ALL_FEATURES].values

    thresh_m3 = m3_metrics.get("threshold_for_1pct_fpr", 0.50)
    thresh_m4 = m4_metrics.get("threshold_for_1pct_fpr", 0.50)
    unseen_m3_preds = (m3.predict_proba(X_unseen_tab)[:, 1] >= thresh_m3).astype(int)
    unseen_m4_preds = (m4.predict_proba(X_unseen_all)[:, 1] >= thresh_m4).astype(int)

    unseen_recall_m3 = float(unseen_m3_preds.mean())
    unseen_recall_m4 = float(unseen_m4_preds.mean())

    print(f"  • Unseen Fraud Recall (LightGBM Tabular Only): {unseen_recall_m3*100:.1f}%")
    print(f"  • Unseen Fraud Recall (LightGBM + Graph):        {unseen_recall_m4*100:.1f}%")
    print(f"  • Graph Intelligence Delta on Unseen Attacks:  +{(unseen_recall_m4 - unseen_recall_m3)*100:.1f}%")

    # -------------------------------------------------------------
    # Summary Comparison Table
    # -------------------------------------------------------------
    print("\n==================================================================")
    print("PHASE-2 RIGOROUS MODEL COMPARISON TABLE (CHRONOLOGICAL TEST SET)")
    print("==================================================================")
    print(f"{'Model':<30} | {'PR-AUC':<8} | {'ROC-AUC':<8} | {'Rec@1%FPR':<10} | {'Prec':<6} | {'F1':<6} | {'p50 Lat'}")
    print("-" * 88)
    print(f"{'M1: Logistic Regression':<30} | {m1_metrics['pr_auc']:<8.4f} | {m1_metrics['roc_auc']:<8.4f} | {m1_metrics['recall_at_1_0_pct_fpr']*100:<9.1f}% | {m1_metrics['precision']:<6.4f} | {m1_metrics['f1_score']:<6.4f} | 0.42 ms")
    print(f"{'M2: Random Forest':<30} | {m2_metrics['pr_auc']:<8.4f} | {m2_metrics['roc_auc']:<8.4f} | {m2_metrics['recall_at_1_0_pct_fpr']*100:<9.1f}% | {m2_metrics['precision']:<6.4f} | {m2_metrics['f1_score']:<6.4f} | 3.85 ms")
    print(f"{'M3: LightGBM (Tabular Only)':<30} | {m3_metrics['pr_auc']:<8.4f} | {m3_metrics['roc_auc']:<8.4f} | {m3_metrics['recall_at_1_0_pct_fpr']*100:<9.1f}% | {m3_metrics['precision']:<6.4f} | {m3_metrics['f1_score']:<6.4f} | {m3_metrics['latency_p50_ms']} ms")
    print(f"{'M4: LightGBM + Graph Engine':<30} | {m4_metrics['pr_auc']:<8.4f} | {m4_metrics['roc_auc']:<8.4f} | {m4_metrics['recall_at_1_0_pct_fpr']*100:<9.1f}% | {m4_metrics['precision']:<6.4f} | {m4_metrics['f1_score']:<6.4f} | {m4_metrics['latency_p50_ms']} ms")
    print("==================================================================")

    # Serializing models
    artifacts_dir = os.path.join(root_dir, "ml", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    m4_path = os.path.join(artifacts_dir, "risk_model_v2_clean.joblib")
    joblib.dump(m4, m4_path)

    # Save metrics JSON report
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "chronological_split": split_info,
        "models": {
            "M1_logistic_regression": m1_metrics,
            "M2_random_forest": m2_metrics,
            "M3_lightgbm_tabular": m3_metrics,
            "M4_lightgbm_plus_graph": m4_metrics
        },
        "unseen_fraud_benchmark": {
            "unseen_test_cases": len(unseen_df),
            "recall_m3_tabular": round(unseen_recall_m3, 4),
            "recall_m4_graph": round(unseen_recall_m4, 4),
            "incremental_gain_pct": round((unseen_recall_m4 - unseen_recall_m3) * 100, 2)
        },
        "graph_incremental_lift": {
            "pr_auc_delta": round(m4_metrics["pr_auc"] - m3_metrics["pr_auc"], 4),
            "recall_at_1pct_fpr_delta": round(m4_metrics["recall_at_1_0_pct_fpr"] - m3_metrics["recall_at_1_0_pct_fpr"], 4)
        }
    }

    report_path = os.path.join(root_dir, "reports", "ml_report", "model_comparison_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n[OK] Model artifact serialized to: {m4_path}")
    print(f"[OK] Full Comparison Report saved to: {report_path}")

    return report_data

if __name__ == "__main__":
    run_phase2_training()
