# upay Pulse — Hackathon Demo Guide & Scenario Playbook
**Document Version:** 1.0.0  
**Phase:** Phase 1 — Architecture  

---

## 1. Demo Credentials & Test Accounts

All demo accounts are populated with deterministic synthetic data:

| Role | Email / Phone | Password | Master Freeze PIN | Initial State |
| :--- | :--- | :--- | :---: | :--- |
| **Customer (Normal)** | `customer@example.com`<br>`+8801700000001` | `Demo@1234` | `1234` | Balance: ৳500.00, Normal history |
| **Customer (Mule Target)** | `victim@example.com`<br>`+8801700000002` | `Demo@1234` | `4321` | Balance: ৳25,000.00, Suspicious incoming |
| **Agent / Merchant** | `agent@example.com`<br>`+8801800000001` | `Demo@1234` | `N/A` | Cash: ৳45,000, Float: ৳120,000 (Savar Zone) |
| **Risk Analyst / Admin** | `admin@example.com`<br>`+8801900000001` | `Admin@1234` | `N/A` | Full Access to Risk Console |

---

## 2. 5-Minute Hackathon Demo Script (0:00 - 5:00)

### 0:00 - 1:00 | The Problem & Vision
- Open the presentation with the MFS trilemma in Bangladesh:
  1. *Security Vulnerability:* Rapid account takeover and money-mule syndicates targeting vulnerable users.
  2. *Customer Liquidity Stress:* Unpredicted month-end deficits causing failed emergency micro-payments.
  3. *Agent Float Depletion:* Garment factories on salary days draining agent cash, causing business loss.
- Introduce **upay Pulse**: An integrated AI ecosystem connecting Customer, Agent, and Risk teams.

### 1:00 - 2:15 | Pillar 1: SecurityAI
- Login as `victim@example.com`.
- Attempt a high-risk abnormal transfer of ৳24,500 at 2:30 AM to an unknown recipient.
- **LightGBM Risk Engine** intercepts the transfer: Risk Score `0.89` (High Risk - Blocked).
- Trigger **Master Freeze**: Customer enters PIN `4321`. In `<50ms`, active sessions are severed and outgoing transactions locked.
- Switch to **Central Risk Console (`admin@example.com`)**:
  - Live Radar shows the flagged transaction.
  - Open **Money-Mule Graph**: Visualizes the NetworkX fan-out ring showing the scam syndicate routing funds toward a cash-out agent in Savar.

### 2:15 - 3:30 | Pillar 2: CustomerAI
- Login as `customer@example.com` (Balance: ৳500).
- Attempt a merchant payment of ৳520.
- **upay Grace** activates: The system explains that due to high reliability (`0.92`), a simulated micro-overdraft of ৳20 is approved. Transaction succeeds!
- Open the **Bangla Voice Financial Coach**:
  - Speak / Type: *"Ei mashe amar khoroch kemon holo?"*
  - The voice coach speaks back in natural Bangla with an instant breakdown of monthly expenses and utility bills.
- Show **Idle Cash Micro-FDR**: Proactive advice on ৳2,000 idle cash for 15+ days.

### 3:30 - 4:30 | Pillar 3: AgentAI
- Login as `agent@example.com` (Savar Industrial Zone).
- Open Agent Dashboard:
  - **XGBoost Liquidity Forecast** predicts a +280% cash-out surge on Thursday (Factory Salary Day).
  - Recommended Float action: *"Increase float by ৳80,000 before 09:00 AM."*
- Demonstrate the **Software Soundbox**:
  - Customer completes payment: The agent terminal immediately announces in clear audio: *"Payment received: 500 taka."*
- Show the **Anti-Screenshot Dynamic Payment Badge**: Animated rotating visual nonce that makes static screenshot scams impossible.

### 4:30 - 5:00 | Measured Technical Impact & Wrap-up
- Display real measured metrics from the live system:
  - Master Freeze Execution Latency: `< 45ms`.
  - LightGBM Risk Model ROC-AUC: `> 0.90` on 50k synthetic transactions.
  - Zero external hardware needed for Agent Soundbox.
