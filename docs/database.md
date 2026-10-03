# upay Pulse — Database Architecture Specification
**Document Version:** 1.0.0  
**Phase:** Phase 1 — Architecture  
**Database Engine:** PostgreSQL 18 (with SQLite dialect fallback for isolated unit tests)  

---

## 1. Entity-Relationship Overview

The database schema is designed with strict relational integrity, foreign key cascading constraints, unique indexes, and audit timestamps.

```
                           ┌──────────────┐
                           │    users     │
                           └──────┬───────┘
                                  │ 1:1
              ┌───────────────────┴───────────────────┐
              ▼                                       ▼
    ┌───────────────────┐                   ┌───────────────────┐
    │ customer_profiles │                   │  agent_profiles   │
    └─────────┬─────────┘                   └─────────┬─────────┘
              │ 1:N                                   │ 1:N
              ├───────────────────┐                   ├───────────────────┐
              ▼                   ▼                   ▼                   ▼
    ┌───────────────────┐ ┌───────────────┐ ┌───────────────────┐ ┌───────────────┐
    │   transactions    │ │ scam_reports  │ │ agent_liquidity   │ │ dynamic_qr_   │
    │  (sender/receiver)│ └───────┬───────┘ │   _forecasts      │ │   badges      │
    └─────────┬─────────┘         │         └───────────────────┘ └───────────────┘
              │ 1:1               ▼
              ├───────────► ┌───────────────┐
              ▼             │  mule_nodes   │
    ┌───────────────────┐   │  mule_edges   │
    │    risk_scores    │   └───────────────┘
    └───────────────────┘
```

---

## 2. Table Specifications

### 2.1 `users`
Core identity table managing credentials, global status, and role-based access.
- `id` (UUID / String, Primary Key)
- `phone` (VARCHAR(15), Unique, Indexed) — e.g., `+8801700000001`
- `email` (VARCHAR(255), Unique, Indexed)
- `hashed_password` (VARCHAR(255), Not Null)
- `role` (ENUM: `CUSTOMER`, `AGENT`, `RISK_ANALYST`, `ADMIN`)
- `status` (ENUM: `ACTIVE`, `FROZEN`, `SUSPENDED`, `CLOSED`)
- `is_frozen` (BOOLEAN, Default: `false`)
- `freeze_pin_hash` (VARCHAR(255), Nullable) — 4-6 digit emergency freeze PIN
- `created_at` (TIMESTAMP WITH TIME ZONE, Default: `NOW()`)
- `updated_at` (TIMESTAMP WITH TIME ZONE, Default: `NOW()`)

### 2.2 `customer_profiles`
Customer-specific financial attributes, simulated balances, and behavioral baselines.
- `id` (UUID / String, Primary Key)
- `user_id` (UUID, Foreign Key -> `users.id`, Unique)
- `full_name` (VARCHAR(100), Not Null)
- `profession` (VARCHAR(50)) — e.g., `Factory Worker`, `Student`, `Executive`
- `location` (VARCHAR(100)) — e.g., `Gazipur`, `Dhanmondi, Dhaka`
- `wallet_balance` (NUMERIC(14, 2), Default: `0.00`)
- `grace_balance` (NUMERIC(14, 2), Default: `0.00`) — Outstanding micro-overdraft
- `reliability_score` (NUMERIC(4, 2), Default: `0.85`) — [0.00 to 1.00]
- `avg_monthly_inflow` (NUMERIC(14, 2), Default: `15000.00`)
- `avg_monthly_outflow` (NUMERIC(14, 2), Default: `14000.00`)
- `created_at`, `updated_at`

### 2.3 `agent_profiles`
Merchant / Agent operational liquidity records and geo-clusters.
- `id` (UUID / String, Primary Key)
- `user_id` (UUID, Foreign Key -> `users.id`, Unique)
- `agent_code` (VARCHAR(20), Unique, Indexed) — e.g., `AGT-1042`
- `store_name` (VARCHAR(120), Not Null)
- `location_cluster` (VARCHAR(100)) — e.g., `Savar Garment Zone`, `Chittagong Port`
- `cash_balance` (NUMERIC(14, 2), Default: `50000.00`)
- `float_balance` (NUMERIC(14, 2), Default: `100000.00`)
- `daily_cash_out_volume` (NUMERIC(14, 2), Default: `0.00`)
- `created_at`, `updated_at`

### 2.4 `transactions`
Unified immutable ledger of all simulated fund movements.
- `id` (UUID / String, Primary Key)
- `transaction_reference` (VARCHAR(32), Unique, Indexed) — e.g., `TXN-8F4D92A1`
- `sender_id` (UUID, Foreign Key -> `users.id`, Indexed)
- `receiver_id` (UUID, Foreign Key -> `users.id`, Indexed)
- `agent_id` (UUID, Foreign Key -> `users.id`, Nullable, Indexed)
- `amount` (NUMERIC(14, 2), Not Null)
- `transaction_type` (ENUM: `SEND_MONEY`, `CASH_IN`, `CASH_OUT`, `MERCHANT_PAY`, `BILL_PAY`, `RECHARGE`)
- `status` (ENUM: `COMPLETED`, `PENDING_REVIEW`, `BLOCKED`, `CANCELLED_FREEZE`)
- `is_flagged_fraud` (BOOLEAN, Default: `false`)
- `idempotency_key` (VARCHAR(64), Unique, Indexed)
- `created_at` (TIMESTAMP WITH TIME ZONE, Indexed)

### 2.5 `risk_scores`
Real-time LightGBM inference logs and explainability feature vectors.
- `id` (UUID / String, Primary Key)
- `transaction_id` (UUID, Foreign Key -> `transactions.id`, Unique, Indexed)
- `risk_score` (NUMERIC(4, 3), Not Null) — [0.000 to 1.000]
- `risk_level` (ENUM: `LOW`, `MEDIUM`, `HIGH`)
- `decision` (ENUM: `ALLOW`, `FRICTION_CHALLENGE`, `BLOCK_AND_FLAG`)
- `reasons` (JSONB / TEXT) — Top contributing SHAP/heuristic factors
- `inference_latency_ms` (NUMERIC(6, 2))
- `created_at` (TIMESTAMP WITH TIME ZONE)

### 2.6 `scam_reports`
User-reported fraud complaints initiating graph intelligence sweeps.
- `id` (UUID / String, Primary Key)
- `reporter_id` (UUID, Foreign Key -> `users.id`, Indexed)
- `reported_account` (VARCHAR(15), Indexed)
- `transaction_id` (UUID, Foreign Key -> `transactions.id`, Nullable)
- `reason` (VARCHAR(255), Not Null)
- `status` (ENUM: `SUBMITTED`, `ANALYZING`, `CONFIRMED_FRAUD`, `DISMISSED`)
- `cluster_id` (VARCHAR(64), Nullable, Indexed)
- `created_at` (TIMESTAMP WITH TIME ZONE)

### 2.7 `mule_graph_nodes` & `mule_graph_edges`
Persistent representation of detected money-mule communities.
- Nodes: `node_id`, `account_number`, `cluster_id`, `node_type`, `risk_score`, `in_degree`, `out_degree`
- Edges: `edge_id`, `source_node`, `target_node`, `total_amount`, `velocity_minutes`, `is_fan_out`

### 2.8 `freeze_actions`
Audit log of emergency lockdowns.
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key -> `users.id`, Indexed)
- `action_type` (ENUM: `MASTER_FREEZE_TRIGGERED`, `MANUAL_ADMIN_FREEZE`, `UNFREEZE_VERIFIED`)
- `sessions_revoked` (INTEGER)
- `pending_cancelled` (INTEGER)
- `response_time_ms` (NUMERIC(6, 2))
- `initiated_ip` (VARCHAR(45))
- `created_at` (TIMESTAMP WITH TIME ZONE)

### 2.9 `cash_flow_forecasts` & `grace_overdraft_requests`
Customer financial health projections and micro-overdraft ledger.
- `cash_flow_forecasts`: `customer_id`, `projected_date`, `forecast_inflow`, `forecast_outflow`, `predicted_balance`, `is_deficit_risk`
- `grace_overdraft_requests`: `customer_id`, `transaction_id`, `requested_amount`, `status`, `repaid_amount`, `created_at`

### 2.10 `micro_fdr_accounts`
Idle-cash term deposit contracts.
- `id`, `customer_id`, `principal_amount`, `term_days`, `interest_rate_pct`, `start_date`, `maturity_date`, `status`

### 2.11 `agent_liquidity_forecasts` & `agent_cash_events`
AgentAI cash-out demand predictions.
- `agent_liquidity_forecasts`: `agent_id`, `target_date`, `predicted_cash_out`, `confidence_interval_low`, `confidence_interval_high`, `recommended_float`, `surge_flag`

### 2.12 `audit_logs` & `notifications`
Comprehensive system compliance and user alerting.
- `audit_logs`: `id`, `actor_id`, `actor_role`, `action`, `resource`, `payload_hash`, `timestamp`
- `notifications`: `id`, `user_id`, `title`, `message`, `type`, `is_read`, `created_at`
