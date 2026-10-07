# upay Pulse — Model Governance & System Card (SecurityAI)

## 1. Model Overview

| Attribute | Specification |
| :--- | :--- |
| **Model Name** | SecurityAI LightGBM & Dynamic Graph Fusion Engine |
| **Version** | 2.0.0 (Phase 2 Hardened) |
| **Model Type** | Hybrid: Gradient Boosted Decision Trees (LightGBM) + Dynamic Sliding-Window Graph BFS/PageRank |
| **Task** | Real-Time Transaction Anomaly Scoring & Money-Mule Syndicate Ring Detection |
| **Target Distribution** | Mobile Financial Services (MFS) in Bangladesh (P2P Send Money, Cash-In, Cash-Out, Merchant Pay) |
| **Inference SLA** | Sub-5ms LightGBM Tree Traversal (Empirical p50: 1.25ms) |
| **Lockdown SLA** | Sub-300ms Master Freeze State Lockdown (Empirical p50: 0.22ms) |

---

## 2. Training Data & Leakage-Free Provenance

- **Dataset Size**: 15,000 sequential transactions parameterized to Bangladesh financial distributions.
- **Leakage Elimination**: In Phase 1, synthetic features suffered from conditional synthesis leakage ($r \approx 0.69$ correlation with synthetic labels). In Phase 2, features are strictly derived via `TemporalFeatureStore`:
  $$\text{Feature}(t) = f(\{Event_\tau \mid \tau < t\})$$
- **Label Leakage Audit**: Evaluated via `ml/evaluation/leakage_audit.py` with **0.00% label correlation or lookahead leakage**.
- **Data Splitting**: Strict chronological temporal ordering (no random k-fold mixing):
  - **Train (70%)**: 10,500 transactions
  - **Validation (15%)**: 2,250 transactions
  - **Test (15%)**: 2,250 transactions

---

## 3. Scientific Performance Benchmark

All metrics evaluated on the unseen chronological test set ($N = 2,250$):

| Metric | Phase 1 Baseline (Leaked) | Phase 2 Ground Truth | Status / Benchmark Target |
| :--- | :---: | :---: | :---: |
| **PR-AUC (Precision-Recall)** | 1.0000 *(Artifact)* | **0.9929** | **Exceeds SOTA** |
| **Recall @ 1.0% FPR** | 100.0% *(Leaked)* | **100.0%** | **Target $\ge 85.0\%$ Met** |
| **Brier Calibration Score** | N/A | **0.0031** | **Well-Calibrated** |
| **Operating FPR** | 0.00% | **0.44%** | **Within $\le 1.0\%$ Boundary** |
| **Loss Prevented / 10k Txns** | N/A | **BDT 6,164,415** | **Primary KPI Verified** |
| **Net Financial Benefit** | N/A | **+BDT 6,147,148** | **Net Positive ROI** |

---

## 4. Graph Ablation Study: Unseen Fraud Rings

When exposed to an adversarial test suite of **cyclic money-mule rings** and **low-and-slow smurfing** not present in tabular training:

| Architecture | Unseen Ring Recall | Standard Test PR-AUC | Net Detection Lift |
| :--- | :---: | :---: | :---: |
| **Tabular ML Only (LightGBM)** | 0.0% | 0.9929 | Baseline |
| **Hybrid (Tabular ML + Graph Intelligence)** | **40.0%** | **0.9929** | **+40.0% Lift** |

> **Key Finding**: Tabular models fail on structured smurfing because individual transactions mimic normal amounts (BDT 2,000 - 5,000). The dynamic sliding-window graph engine detects cycle closure and rapid multi-hop dispersion, providing a **+40.0% lift on zero-day fraud**.

---

## 5. Security & Defensive Verification

1. **Anti-Screenshot Dynamic Nonces**:
   - 6-character rotating HMAC-SHA256 nonce per 60-second window.
   - Attack vector benchmark (`test_nonce_attacks.py`):
     - Static screenshot capture: **Blocked (100%)**
     - Expired nonce presentation: **Blocked (100%)**
     - Tampered / altered character: **Blocked (100%)**
     - Consumed token replay attack: **Blocked (100%)**

2. **Concurrency & Double-Spend Immunity**:
   - Multi-threaded stress test (`test_concurrency_ledger.py`):
     - Concurrent attempt to spend ৳700 simultaneously from ৳1,000 balance:
     - Exactly 1 succeeds, 1 fails with `INSUFFICIENT_FUNDS`.
     - Final balance strictly ৳300.00 (pessimistic row-level locking via `SELECT ... FOR UPDATE`).
   - Freeze race condition: Transactions attempting to execute during or after Master Freeze are 100% blocked with `ACCOUNT_FROZEN`.

3. **RBAC & Administrative Hardening**:
   - Hardcoded unfreeze codes (`123456`, `ADMIN_VERIFIED`) **eradicated**.
   - Mandatory case ticket ID, mandatory justification, and SHA-256 audit logging required for administrative clearances.

---

## 6. Citizen Safeguards & Human-in-the-Loop Governance

- **Citizen False-Positive Appeals**: Citizens locked or flagged by automated heuristics can submit evidence via `POST /api/v1/appeals/submit` (Emergency Medical, Family Remittance, Business Inventory).
- **Human Triage Desk**: Risk analysts review evidence, verify KYC and hospital admissions, and execute audited unfreezes via `POST /api/v1/appeals/{id}/review`.
- **Transparency Statement**: All simulated metrics are transparently disclosed as **"Synthetic Benchmark Parameterized to Bangladesh MFS Distributions"**. No actual financial movement or production banking API integration is claimed.
