# upay Pulse — Machine Learning & Graph Intelligence Specification
**Document Version:** 1.0.0  
**Phase:** Phase 1 — Architecture  

---

## 1. SecurityAI: LightGBM Transaction Risk Classifier

### 1.1 Objective
Produce a calibrated risk score $S \in [0.000, 1.000]$ for each transaction in under 50ms, classifying risk tiers:
- **Low Risk:** $S < 0.40$ (Instant Approval)
- **Medium Risk:** $0.40 \le S < 0.75$ (Friction Challenge / SMS OTP verification)
- **High Risk:** $S \ge 0.75$ (Block and alert Risk Console)

### 1.2 Feature Store Architecture
```
Features Vector (14 features):
├── [F1] amount: Normalized transaction amount (BDT)
├── [F2] amount_zscore_user: Deviation from user's historical 30-day mean
├── [F3] velocity_10m: Count of transactions by sender in prior 10 minutes
├── [F4] velocity_1h: Count of transactions by sender in prior 60 minutes
├── [F5] hour_of_day: 0 to 23
├── [F6] is_night_time: Binary flag (1 if 01:00 AM - 05:30 AM)
├── [F7] account_age_days: Days since user registration
├── [F8] is_new_recipient: Binary flag (1 if sender never sent to receiver)
├── [F9] receiver_in_degree_24h: Number of distinct senders sending to receiver
├── [F10] receiver_risk_rating: Historical risk score of receiver
├── [F11] device_switch_detected: Binary flag (different user-agent or IP subnet)
├── [F12] rapid_drain_pct: Transaction amount / current wallet balance
├── [F13] failed_pin_attempts_prior: Failed attempts before this attempt
└── [F14] tx_type_risk_weight: Base prior risk by type (Cash-Out > Send Money > Merchant Pay)
```

### 1.3 Model Hyperparameters & Training Setup
- **Algorithm:** `LightGBM` (with scikit-learn `HistGradientBoostingClassifier` fallback)
- **Objective:** `binary` (cross-entropy logloss)
- **Metrics Tracked:** ROC-AUC, Precision@Top 5%, Recall@High Risk, Confusion Matrix.
- **Explainability:** Feature importance and top 3 heuristic reason generation per inference.

---

## 2. SecurityAI: Money-Mule Graph Intelligence (NetworkX)

### 2.1 Graph Formulation
- Directed Graph $G = (V, E)$ where:
  - $V$ (Vertices): Customer Wallets, Mule Accounts, Merchant/Cash-Out Agents.
  - $E$ (Edges): Transactions with weights $\sum \text{Amount}$, timestamps, and frequency.

### 2.2 Mule Ring Detection Algorithms
1. **Fan-Out Anomaly Index:** High ratio of incoming funds followed by rapid outward distribution to multiple secondary accounts within 30 minutes.
2. **Cash-Out Convergence:** Multiple secondary accounts transferring concentrated funds into a single Cash-Out Agent node.
3. **Cycle & Directed Path Tracing:** NetworkX simple cycles and short-path traversal from flagged scam accounts to terminus liquidation nodes.

---

## 3. AgentAI: XGBoost Liquidity Forecaster

### 3.1 Objective
Predict expected hourly and daily cash-out volume for an agent location cluster, preventing cash stock-outs and optimizing float capital.

### 3.2 Feature Matrix:
- Historical 7-day, 14-day, and 30-day rolling cash-out volumes.
- `day_of_week` (Weekend surge vs weekday).
- `day_of_month` (Salary days: 1st - 7th of month trigger +250% surge).
- `is_factory_zone` (Industrial cluster multiplier).
- `festival_spike_flag` (Eid / Puja bonus week indicator).
- `current_cash` vs `current_float` ratio.

---

## 4. CustomerAI: Cash-Flow Trajectory & Grace Scoring

### 4.1 Cash-Flow Time-Series Model
Autoregressive daily balance projection:
$$B_{t+k} = B_t + \sum_{i=1}^k (\hat{I}_{t+i} - \hat{O}_{t+i})$$
If $B_{t+k} < \text{Buffer Threshold}$ within 5 days, emit proactive advice alert.

### 4.2 upay Grace (Simulated Micro-Overdraft)
Explainable logistic scoring model assessing:
- Customer reliability score (0.0 to 1.0).
- Historical repayment on past Grace requests.
- Account age (> 30 days).
- Inflow regularity.
- Output: Approved Grace Limit (৳20 to ৳500), automatically collected on the next cash-in.
