# upay Pulse — Cybersecurity & Access Control Specification
**Document Version:** 1.0.0  
**Phase:** Phase 1 — Architecture  

---

## 1. Role-Based Access Control (RBAC) Matrix

| Resource / Endpoint | Anonymous | CUSTOMER | AGENT | RISK_ANALYST | ADMIN |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `/api/v1/auth/register`, `/login` | **Allow** | **Allow** | **Allow** | **Allow** | **Allow** |
| `/api/v1/transactions/send` | Deny | **Own Account** | Deny | Deny | Deny |
| `/api/v1/freeze/trigger` | Deny | **Own Account** | Deny | Deny | **Any (Override)** |
| `/api/v1/customer/*` | Deny | **Own Profile** | Deny | Deny | Deny |
| `/api/v1/agent/*` | Deny | Deny | **Own Agent ID** | Read-Only | Full Access |
| `/api/v1/risk/*` | Deny | Deny | Deny | **Full Access** | **Full Access** |
| `/api/v1/scams/graph` | Deny | Deny | Deny | **Full Access** | **Full Access** |
| `/api/v1/audit/logs` | Deny | Deny | Deny | Read-Only | **Full Access** |

---

## 2. Emergency Master Freeze State Machine

The Master Freeze is designed to respond in sub-300ms upon customer suspicion of account takeover or device snatching.

```
       [ ACTIVE ] ─────────────► (Customer Enters Freeze PIN)
           │                                 │
           │                                 ▼
           │                     [ PIN Validation <15ms ]
           │                                 │
           │                 ┌───────────────┴───────────────┐
           │                 ▼ Valid                         ▼ Invalid
           │     [ LOCKDOWN TRANSITION ]            [ Increment Failed Count ]
           │                 │                      (Lock after 3 failures)
           │     ┌───────────┼───────────┐
           │     ▼           ▼           ▼
           │  Revoke     Cancel       Broadcast
           │  Active     Pending      Security
           │  JWTs       Transfers    Alert
           │     │           │           │
           │     └───────────┼───────────┘
           │                 ▼
           │             [ FROZEN ]
           │                 │
           │                 ▼ (Verified Customer Support / In-Person KYC)
           └────────────► [ ACTIVE ]
```

### Security Enforcement Rules for Frozen State:
1. All outgoing simulated transfers, payments, and cash-outs are rejected immediately with HTTP 403 `ACCOUNT_FROZEN`.
2. Pending uncollected cash-out tokens are revoked.
3. Read-only access to transaction history remains permitted so customers can inspect suspicious activity.
4. Unfreeze requires verified re-authentication or administrator verification.

---

## 3. Cryptographic Storage & Session Handling

- **Passwords & Freeze PINs:** Salted and hashed using `bcrypt` (work factor 12). The freeze PIN is stored as a separate hash (`freeze_pin_hash`) ensuring separation of concerns.
- **JWT Tokens:** Signed using `RS256` or `HS256` with strict short TTL (Access Token: 30 minutes, Refresh Token: 7 days).
- **Session Revocation:** Redis / In-memory blocklist tracking `jti` (JWT ID) or user-level `token_revoked_at` timestamp.

---

## 4. Prompt Injection & AI Tool Abuse Defenses

1. **No Direct SQL Execution:** The LLM orchestration layer never receives database handles or raw query capabilities.
2. **Deterministic Tool Dispatch:** Tools accept strictly typed Pydantic parameter schemas (e.g., `get_spending_summary(period: "current_month")`).
3. **Customer Data Boundary Isolation:** The voice coach query pipeline injects the authenticated `user_id` server-side from the verified JWT; user prompts cannot supply or spoof another user's ID.
4. **Sanitized Output Filters:** Outbound LLM text responses are scanned for sensitive leaks (passwords, tokens, raw UUIDs, unmasked phone numbers).
