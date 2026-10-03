# upay Pulse — System Architecture Specification
**Document Version:** 1.0.0  
**Phase:** Phase 1 — Architecture  
**Status:** Approved  

---

## 1. Executive Overview

**upay Pulse** is an integrated, AI-powered Mobile Financial Services (MFS) Intelligence Ecosystem designed for modern financial security, agent liquidity assurance, and customer financial empowerment. 

The platform operates on a continuous feedback intelligence loop:
```
     TRANSACTION DATA (Simulated MFS Stream)
                 ↓
          AI / ML ANALYSIS
   (SecurityAI + CustomerAI + AgentAI)
                 ↓
     RISK / CUSTOMER / AGENT INSIGHTS
                 ↓
     RECOMMENDATION / INTERVENTION
 (Freeze PIN / Grace Overdraft / Float Rebalance)
                 ↓
         SIMULATED ACTION
                 ↓
             NEW DATA
                 ↓
      CONTINUOUS INTELLIGENCE
```

---

## 2. Core Architectural Pillars

### Pillar 1: SecurityAI (Fraud & Risk Intelligence)
- **Real-Time Anomaly Detection:** LightGBM-based scoring model evaluating every transaction in sub-50ms latency across 14+ engineered behavioral features.
- **Master Freeze State Machine:** Customer-triggered emergency lockdown revoking sessions, freezing outgoing transfers, and cancelling pending cash-outs in under 300ms.
- **Money-Mule Graph Intelligence:** NetworkX topological network analysis identifying mule rings, rapid fan-out topologies, and cash-out convergence clusters.
- **Scam Reporting Engine:** Customer-driven flagging workflow integrated directly into the Risk Console live radar.

### Pillar 2: CustomerAI (Financial Health & Voice Assistance)
- **Cash-Flow Forecasting:** Time-series autoregressive balance trajectory forecasting with 5-day proactive deficit alerts.
- **Spending Categorization & Trends:** Deep breakdown across recharge, utilities, merchant payment, and cash-out.
- **upay Grace (Simulated Micro-Overdraft):** Explainable logistic credit-scoring model providing instant micro-liquidity (৳20 - ৳500) for transaction completion.
- **Idle Cash Micro-FDR Engine:** Automated detection of idle surplus funds (15+ days) generating micro-term deposit recommendations.
- **Bangla Voice Financial Coach:** Real-time conversational AI supporting spoken Bangla, Banglish, and text queries via modular LLM and speech abstractions.

### Pillar 3: AgentAI (Merchant & Liquidity Intelligence)
- **Liquidity & Cash-Out Forecasting:** XGBoost Regressor forecasting hourly and daily cash demands based on factory salary cycles, weekends, and festival surges.
- **Surge Alert System:** Proactive notifications for float shortages, low cash, and high demand windows.
- **Software-Only Soundbox:** Browser-native and Web Audio API synthesized audio announcements (*"Payment received: 500 taka"*) eliminating hardware cost.
- **Anti-Screenshot Dynamic Payment Badge:** Dynamic animated SVG verification tokens with rotating nonces preventing static screenshot fraud.

---

## 3. High-Level Technology Stack & Rationale

| Layer | Selected Technology | Technical Rationale |
| :--- | :--- | :--- |
| **Frontend UI** | **React 18 + TypeScript + Vite + Tailwind CSS** | Ultra-lean memory footprint (~120 MB RAM vs 1.5+ GB in Next.js SSR), instantaneous HMR, robust component isolation, and seamless single-origin static serving. |
| **UI Components** | **Fintech Design Tokens + Lucide Icons + Recharts** | Professional dark/glassmorphic aesthetics, interactive responsive financial charts, and accessible form controls. |
| **Backend API** | **Python 3.14 + FastAPI + Pydantic v2** | High-performance asynchronous event handling, automatic OpenAPI/Swagger generation, and native integration with Python ML/AI ecosystem. |
| **ORM / Data Layer** | **SQLAlchemy 2.0 (Async/Sync) + psycopg2** | Enterprise-grade query optimization, strict type hinting, robust relational transactions, and multi-dialect compatibility. |
| **Primary Database** | **PostgreSQL 18.6** | Robust ACID transactional guarantees, JSONB support for graph and risk telemetry, and native connection on host port 5432. |
| **Event & Cache Bus** | **Hybrid Redis / Async In-Memory EventBus** | Connects to Redis pub-sub in containerized environments; automatically switches to an in-memory event bus when running standalone locally. |
| **Machine Learning** | **LightGBM 4.7 + XGBoost 3.4 + scikit-learn 1.8** | State-of-the-art gradient boosting for tabular fraud and liquidity regressions with verified Python 3.14 Windows compatibility. |
| **Graph Intelligence** | **NetworkX 3.6** | High-performance in-memory graph algorithms for mule ring detection, degree centrality, and cycle detection. |
| **Voice & LLM** | **Modular Provider Abstraction (Gemini / OpenAI / MockLocal)** | Zero-downtime fallback: runs fully offline with deterministic mock data during hackathon evaluations without external API dependency. |

---

## 4. Multi-Tenant Role Isolation & Boundary Rules

1. **Customer Boundary:**
   - Authenticated customers only possess access to their personal wallet, ledger records, credit scores, and voice interactions.
   - PII masking on all recipient account numbers.
2. **Merchant/Agent Boundary:**
   - Agents can only view their own float balances, historical cash-ins/outs, and assigned area surge forecasts.
   - Customer transaction details are redacted (only amount and confirmation status visible).
3. **Risk Analyst / Admin Boundary:**
   - Full visibility across system-wide transaction streams, mule graph topology, frozen wallets, and model metrics.
   - Strict audit logging for every administrative query or override.

---

## 5. Deployment Topology

- **Standalone Local Mode:** 
  FastAPI server running on `http://127.0.0.1:8000`, Vite UI running on `http://localhost:5173`, connected directly to local PostgreSQL 18.
- **Docker Compose Mode:**
  Multi-container orchestration: `backend`, `frontend`, `postgres`, `redis`.
