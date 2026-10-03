# upay Pulse — Quality Assurance & Testing Specification
**Document Version:** 1.0.0  
**Phase:** Phase 1 — Architecture  

---

## 1. Test Strategy & Quality Gates

The test suite validates correctness, data integrity, and compliance across all components using `pytest` and async test runners.

```
       ┌────────────────────────────────────────────────────────┐
       │                END-TO-END SCENARIO TESTS               │
       │   Freeze Lockdown • Grace Recovery • Scam Graph Link   │
       ├────────────────────────────────────────────────────────┤
       │                INTEGRATION TESTS (API)                 │
       │     FastAPI TestClient • PostgreSQL • Event Bus        │
       ├────────────────────────────────────────────────────────┤
       │                   UNIT TESTS (LOGIC)                   │
       │  Bcrypt Auth • RBAC • LightGBM Inferrer • State Machine │
       └────────────────────────────────────────────────────────┘
```

---

## 2. Test Cases Matrix

### 2.1 Security & Auth
- `test_user_registration_and_hash`: Verifies bcrypt hashing for both password and emergency freeze PIN.
- `test_rbac_customer_isolation`: Ensures customer A cannot read customer B's ledger or profiles (HTTP 403/404).
- `test_master_freeze_state_machine`: Verifies that entering the correct PIN transitions wallet to `FROZEN`, revokes tokens, cancels pending transfers, and blocks subsequent outgoing requests.

### 2.2 Financial Transactions & Ledger
- `test_idempotent_transaction`: Submitting the same transaction with identical idempotency key returns cached result without double-deduction.
- `test_insufficient_balance_grace_trigger`: Transfer of ৳520 with ৳500 balance returns `INSUFFICIENT_FUNDS` with valid Grace eligibility metadata.
- `test_grace_auto_recovery_on_cash_in`: Customer with outstanding Grace balance of ৳20 has it automatically repaid upon next simulated Cash-In of ৳100 (net balance becomes ৳80).

### 2.3 ML Models & Graph Intelligence
- `test_lightgbm_risk_scoring`: Evaluates synthetic transaction features; confirms valid float in range `[0.0, 1.0]` and correct classification tier (`LOW`, `MEDIUM`, `HIGH`).
- `test_networkx_mule_detection`: Injects known fan-out edge pattern (1 source -> 5 intermediate -> 1 agent); verifies graph algorithm correctly flags cluster nodes.
- `test_agent_liquidity_forecaster`: Confirms XGBoost prediction outputs valid non-negative float recommendation and high surge flags on salary days.
