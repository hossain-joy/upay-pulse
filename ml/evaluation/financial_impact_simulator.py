"""
upay Pulse — Synthetic Financial Impact Engine (Workstream 8)
Computes the Primary KPI:
Fraud Loss Prevented / 10,000 Transactions (Subject to FPR <= 1.0%)
Accounts for:
- Fraud loss blocked (BDT)
- Customer friction cost per false positive (150 BDT)
- Human analyst triage operational cost (45 BDT)
- Net Financial Benefit (BDT)
"""

import os
import sys
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

from ml.features.temporal_feature_store import FEATURE_COLUMNS
from ml.graph.temporal_graph_engine import (
    GRAPH_FEATURE_COLUMNS,
    enrich_dataset_with_temporal_graph
)
from ml.training.temporal_split import chronological_split
from ml.evaluation.risk_fusion import compute_graph_structural_risk, fuse_risk_scores

FRICTION_COST_PER_FP = 150.0  # BDT estimated cost of user dissatisfaction/support
ANALYST_COST_PER_TRIAGE = 45.0  # BDT estimated triage cost for manual review

def run_financial_impact_simulation(target_scale: int = 10000) -> dict:
    print("==================================================================")
    print(f"UPAY PULSE: WORKSTREAM 8 — SYNTHETIC FINANCIAL IMPACT ENGINE")
    print(f"Normalized Benchmark Scale: {target_scale:,} Transactions")
    print("==================================================================")

    data_path = os.path.join(root_dir, "data", "synthetic_transactions_clean.csv")
    df = pd.read_csv(data_path)
    df["created_at_dt"] = pd.to_datetime(df["created_at_dt"])
    df = enrich_dataset_with_temporal_graph(df)

    _, _, test_df = chronological_split(df, train_ratio=0.70, val_ratio=0.15)
    n_test = len(test_df)
    scale_factor = float(target_scale) / float(n_test)

    # Load trained model
    model_path = os.path.join(root_dir, "ml", "artifacts", "risk_model_v2_clean.joblib")
    m4 = joblib.load(model_path)

    X_test_all = test_df[FEATURE_COLUMNS + GRAPH_FEATURE_COLUMNS].values
    p_tab = m4.predict_proba(X_test_all)[:, 1]

    s_graph = compute_graph_structural_risk(
        test_df["graph_is_cycle_participant"].values,
        test_df["graph_in_degree_fan_ratio"].values,
        test_df["graph_mule_community_risk"].values,
        test_df["graph_pagerank_score"].values
    )
    p_fused = fuse_risk_scores(p_tab, s_graph)

    # Ground truth
    is_fraud = test_df["is_flagged_fraud"].astype(bool).values
    amounts = test_df["amount"].values

    total_exposure = float(amounts[is_fraud].sum()) * scale_factor
    total_fraud_txns = int(is_fraud.sum() * scale_factor)

    # Policy 1: No Protection Baseline
    baseline_loss = total_exposure

    # Policy 2: Tabular LightGBM Only (Threshold = 0.72)
    tab_blocked = p_tab >= 0.72
    tab_tp = is_fraud & tab_blocked
    tab_fp = (~is_fraud) & tab_blocked
    tab_prevented = float(amounts[tab_tp].sum()) * scale_factor
    tab_friction = float(tab_fp.sum()) * FRICTION_COST_PER_FP * scale_factor
    tab_analyst = float(tab_blocked.sum()) * ANALYST_COST_PER_TRIAGE * scale_factor
    tab_net_benefit = tab_prevented - tab_friction - tab_analyst

    # Policy 3: Full upay Pulse Hybrid (Tabular + Graph) (Threshold = 0.72)
    fused_blocked = p_fused >= 0.72
    fused_tp = is_fraud & fused_blocked
    fused_fp = (~is_fraud) & fused_blocked
    fused_prevented = float(amounts[fused_tp].sum()) * scale_factor
    fused_friction = float(fused_fp.sum()) * FRICTION_COST_PER_FP * scale_factor
    fused_analyst = float(fused_blocked.sum()) * ANALYST_COST_PER_TRIAGE * scale_factor
    fused_net_benefit = fused_prevented - fused_friction - fused_analyst

    # Format comparison table
    print("\n--- SYNTHETIC FINANCIAL BENEFIT COMPARISON (PER 10,000 TXNS) ---")
    print(f"{'Metric':<36} | {'Without Pulse':<15} | {'LightGBM Only':<15} | {'upay Pulse Fused'}")
    print("-" * 90)
    print(f"{'Total Fraud Exposure':<36} | BDT {baseline_loss:>10,.0f} | BDT {baseline_loss:>10,.0f} | BDT {baseline_loss:>10,.0f}")
    print(f"{'Fraud Loss Prevented (Primary KPI)':<36} | BDT {'0':>10} | BDT {tab_prevented:>10,.0f} | BDT {fused_prevented:>10,.0f}")
    print(f"{'Customer Friction Cost (FPs)':<36} | BDT {'0':>10} | BDT {tab_friction:>10,.0f} | BDT {fused_friction:>10,.0f}")
    print(f"{'Analyst Review Overhead':<36} | BDT {'0':>10} | BDT {tab_analyst:>10,.0f} | BDT {fused_analyst:>10,.0f}")
    print(f"{'Net Financial Benefit':<36} | BDT {'0':>10} | +BDT{tab_net_benefit:>9,.0f} | +BDT{fused_net_benefit:>9,.0f}")
    print(f"{'False Positive Rate':<36} | {'0.0%':>14} | {tab_fp.mean()*100:>13.2f}% | {fused_fp.mean()*100:>13.2f}%")
    print("=" * 90)

    reports_dir = os.path.join(root_dir, "reports", "impact_report")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "synthetic_financial_impact.json")

    impact_data = {
        "benchmark_scale": target_scale,
        "disclaimer": "Synthetic benchmark parameterized to published Bangladesh MFS distributions; not real banking rail claims.",
        "primary_kpi_fraud_loss_prevented_bdt": round(fused_prevented, 2),
        "primary_kpi_formula": "Fraud Loss Prevented / 10,000 Transactions subject to FPR <= 1.0%",
        "operating_fpr": round(float(fused_fp.mean()), 4),
        "net_financial_benefit_bdt": round(fused_net_benefit, 2),
        "breakdown": {
            "without_pulse": {
                "fraud_loss_bdt": round(baseline_loss, 2),
                "net_benefit_bdt": 0.0
            },
            "lightgbm_only": {
                "loss_prevented_bdt": round(tab_prevented, 2),
                "friction_cost_bdt": round(tab_friction, 2),
                "analyst_cost_bdt": round(tab_analyst, 2),
                "net_benefit_bdt": round(tab_net_benefit, 2),
                "fpr": round(float(tab_fp.mean()), 4)
            },
            "upay_pulse_fused": {
                "loss_prevented_bdt": round(fused_prevented, 2),
                "friction_cost_bdt": round(fused_friction, 2),
                "analyst_cost_bdt": round(fused_analyst, 2),
                "net_benefit_bdt": round(fused_net_benefit, 2),
                "fpr": round(float(fused_fp.mean()), 4)
            }
        }
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(impact_data, f, indent=2)

    print(f"\n[OK] Impact analysis serialized to: {report_path}")
    print("==================================================================")
    return impact_data

if __name__ == "__main__":
    run_financial_impact_simulation()
