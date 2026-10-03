# upay Pulse — API Architecture & Contract Specification
**Document Version:** 1.0.0  
**Base URL:** `/api/v1`  
**Protocol:** RESTful JSON + WebSockets  

---

## 1. Authentication & Security Headers

All protected endpoints require an `Authorization` header containing a valid Bearer JWT:
```http
Authorization: Bearer <access_token>
```
All state-modifying endpoints (`POST`, `PUT`, `DELETE`) require an `Idempotency-Key` header:
```http
Idempotency-Key: <unique_uuid_or_nonce>
```

---

## 2. API Endpoint Registry

### 2.1 Authentication & Profile (`/api/v1/auth`)
- `POST /auth/register` — Create new customer/agent account with hashed freeze PIN.
- `POST /auth/login` — Authenticate credentials, return JWT access token and user role.
- `POST /auth/refresh` — Issue fresh access token from valid refresh token.
- `GET /auth/me` — Retrieve active authenticated user identity and role.
- `POST /auth/logout` — Invalidate current session and revoke tokens.

### 2.2 Transactions & Financial Simulation (`/api/v1/transactions`)
- `POST /transactions/send` — Initiate customer-to-customer or customer-to-merchant transfer. Evaluates risk engine before execution.
- `POST /transactions/cash-out` — Request agent cash-out simulation.
- `POST /transactions/cash-in` — Simulated agent cash-in (auto-recovers active Grace balances).
- `GET /transactions/history` — Paginated transaction ledger with status filters.
- `GET /transactions/{id}` — Detailed ledger record with risk evaluation score.

### 2.3 SecurityAI: Emergency Master Freeze (`/api/v1/freeze`)
- `POST /freeze/trigger` — Customer emergency lockdown with 4-digit Master Freeze PIN.
  - *Payload:* `{"freeze_pin": "1234", "reason": "Suspected device theft"}`
  - *Response:* `{"status": "FROZEN", "sessions_revoked": 2, "pending_cancelled": 1, "latency_ms": 42.1}`
- `GET /freeze/status` — Get current wallet freeze state.
- `POST /freeze/unfreeze` — Verified OTP / Admin verified unfreeze workflow.

### 2.4 SecurityAI: Risk Engine & Scam Graph (`/api/v1/risk` & `/api/v1/scams`)
- `POST /risk/evaluate` — Evaluate real-time LightGBM risk score on candidate transaction.
- `GET /risk/overview` — Risk Console telemetry: High/Med/Low distributions, live alerts.
- `GET /risk/high-risk` — Stream of blocked or flagged suspicious transactions.
- `POST /scams/report` — Customer scam reporting endpoint.
- `GET /scams/graph` — NetworkX topological graph payload for Risk Console canvas.
  - *Response:* `{ nodes: [...], edges: [...], clusters: [...], suspicious_mules: [...] }`

### 2.5 CustomerAI: Financial Intelligence (`/api/v1/customer`)
- `GET /customer/forecast` — Autoregressive 30-day cash-flow forecast and low-balance warnings.
- `GET /customer/spending` — Categorized spending breakdown (Recharge, Food, Bills, Cash-Out).
- `POST /customer/grace/check` — Check eligibility and max allowed overdraft (৳20 - ৳500).
- `POST /customer/grace/apply` — Accept simulated Grace overdraft for pending shortfall.
- `GET /customer/fdr/recommendation` — Retrieve idle-cash micro-deposit offers.
- `POST /customer/fdr/activate` — Confirm simulated Micro-FDR allocation.

### 2.6 CustomerAI: Bangla Voice Financial Coach (`/api/v1/voice`)
- `POST /voice/query` — Send natural language query (Bangla / Banglish text or audio).
  - *Payload:* `{"query_text": "Ei mashe amar khoroch kemon holo?", "session_id": "..."}`
  - *Response:* `{"response_bangla": "এই মাসে আপনার মোট খরচ হয়েছে ৮,৪০০ টাকা...", "audio_url": "/api/v1/voice/audio/123", "insights": {...}}`
- `GET /voice/history` — Prior financial voice coaching conversations.

### 2.7 AgentAI: Merchant Operations (`/api/v1/agent`)
- `GET /agent/dashboard` — Live cash balance, float balance, and today's cash-out demand.
- `GET /agent/forecast` — XGBoost-predicted hourly cash-out surges and recommended float.
- `GET /agent/alerts` — Surge warnings (Factory salary day, Eid rush, float shortage).
- `POST /agent/soundbox/announce` — Generate synthesized soundbox audio payload.
- `GET /agent/badge/verify/{txn_id}` — Verify anti-screenshot dynamic QR nonce status.

### 2.8 Audit & System Observability (`/api/v1/audit` & `/health`)
- `GET /health` — Readiness probe for backend, PostgreSQL, and cache bus.
- `GET /audit/logs` — Immutable audit trail of administrative, freeze, and risk events.

---

## 3. Standard Error Envelope

All API errors return a consistent, safe payload with no raw stack traces exposed:
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Your wallet balance is insufficient to complete this transfer.",
    "details": {
      "current_balance": 500.00,
      "required_amount": 520.00,
      "grace_eligible": true,
      "max_grace_available": 50.00
    },
    "timestamp": "2026-10-03T22:15:00Z"
  }
}
```
