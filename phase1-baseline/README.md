# Phase-1 Baseline Ledger — upay Pulse

This directory captures an immutable freeze of the Phase-1 prototype state, metrics, model artifacts, and test results prior to Phase-2 scientific refactoring.

---

## 📊 Phase-1 Baseline Metrics Ledger

| Benchmark Metric | Phase 1 Value | Measurement Method / Notes |
|:---|:---:|:---|
| **ROC-AUC Score** | **1.0000** | Stratified random split (Flagged as Target Leakage in lines 43–50 of `training/train_risk_model.py`) |
| **PR-AUC (Avg Precision)** | **1.0000** | Inflated due to target label conditional generation |
| **Precision** | **1.0000** | Zero false positives in Phase-1 evaluation test set |
| **Recall** | **1.0000** | Zero false negatives in Phase-1 evaluation test set |
| **F1-Score** | **1.0000** | Harmonic mean of precision & recall |
| **LightGBM Inference (p50)** | **1.37 ms** | Single-sample C++ LightGBM binary latency |
| **LightGBM Inference (p95)** | **1.72 ms** | 95th percentile latency benchmark |
| **Master Freeze SLA** | **12.4 ms** | Sub-300ms emergency account lockdown |
| **Graph Syndicate Detection**| **42.1 ms** | NetworkX PageRank & Weakly Connected Components |
| **Dynamic Nonce Verification**| **14.6 ms** | SHA-256 rotating 6-char HMAC validation |
| **Soundbox Audio Chime** | **8.2 ms** | HTML5 Web Audio API chord synthesis |
| **Voice Coach Latency** | **5,260 ms** | Gemini 2.5 Flash streaming API |
| **Automated Backend Tests** | **38 / 38 passed** | 100% test pass rate across all 11 test modules |

---

## 🗂️ Frozen Artifacts Inventory

- [`model/risk_model_p1.joblib`](file:///d:/diu_hackathon/phase1-baseline/model/risk_model_p1.joblib): Original trained LightGBM binary model artifact.
- [`metrics/risk_metrics_p1.json`](file:///d:/diu_hackathon/phase1-baseline/metrics/risk_metrics_p1.json): Original reported metrics payload.
- [`data/synthetic_transactions_p1.csv`](file:///d:/diu_hackathon/phase1-baseline/data/synthetic_transactions_p1.csv): Original 50,000 synthetic transaction dataset snapshot.
- [`test-results/pytest_p1_results.txt`](file:///d:/diu_hackathon/phase1-baseline/test-results/pytest_p1_results.txt): Full execution log of 38/38 passing pytest run.
- [`verify_phase1_baseline.py`](file:///d:/diu_hackathon/phase1-baseline/verify_phase1_baseline.py): Script to inspect and verify the preserved baseline model.
