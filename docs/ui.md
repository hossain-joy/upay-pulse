# upay Pulse — UI/UX Design & Frontend Architecture
**Document Version:** 1.0.0  
**Phase:** Phase 1 — Architecture  

---

## 1. Visual Design Philosophy & Aesthetics

**upay Pulse** adheres to high-tier modern fintech design standards:
- **Palette:** Deep Navy (`#0B1120`), Dark Slate (`#1E293B`), Vivid Emerald (`#10B981`, Safe/Approval), Amber Warning (`#F59E0B`, Friction/Grace), Crimson (`#EF4444`, High Risk/Freeze), Cyan Pulse (`#06B6D4`, AI Intelligence).
- **Glassmorphism:** Layered frosted cards (`backdrop-blur-md`, subtle border highlights `border-white/10`).
- **Typography:** Modern clean sans-serif (Inter / Outfit) with numerical tabular lining for transaction amounts.
- **Micro-Animations:** Fluid CSS transitions on risk meters, pulse rings on live radars, and animated SVG nonces on the dynamic payment badge.

---

## 2. Portal Screen Breakdown

### 2.1 Customer Portal (`/customer/*`)
1. **Dashboard:** Live wallet balance, quick actions (Send, Cash Out, Master Freeze), recent ledger feed, proactive AI insight card.
2. **Transaction History & Detail:** Search, filter, date picker, detailed breakdown with risk tag.
3. **Emergency Master Freeze:** High-urgency modal requiring 4-digit PIN with clear explanation of lockdown state.
4. **Cash-Flow Forecast & Spending:** Recharts line chart showing projected 30-day liquidity trajectory.
5. **upay Grace (Simulated Micro-Overdraft):** Shortfall assistance card with eligibility score, terms, and 1-click confirmation.
6. **Idle Cash Micro-FDR:** Surplus savings recommender card with projected interest returns.
7. **Bangla Voice Financial Coach:** Interactive conversational widget with voice microphone input, waveform animation, and audio playback.
8. **Scam Reporting Modal:** Rapid 3-step complaint submission linking suspicious transaction to the Risk Console.

### 2.2 Merchant / Agent Portal (`/agent/*`)
1. **Agent Dashboard:** Dual cash vs float balance meter, daily cash-out volume, active liquidity state.
2. **Liquidity Surge Forecast:** Hourly demand projection curve highlighting salary days and weekend spikes.
3. **Software Soundbox Terminal:** Audio announcement player with volume slider, simulated test triggers, and visual receipt banner.
4. **Anti-Screenshot Payment Verifier:** Scanner & verification view matching customer dynamic QR nonces.

### 2.3 Central Risk Console (`/risk/*`)
1. **Risk Radar & Overview:** Live transaction ticker, risk score distribution (Low/Med/High), active freeze counters.
2. **NetworkX Money-Mule Graph Canvas:** Interactive SVG/Canvas topological graph showing nodes (customers, mules, agents) and animated fan-out transaction flows.
3. **High-Risk Case Manager:** Deep-dive inspection panel with SHAP feature importance explainability cards.
4. **Model Performance Hub:** Real measured ROC-AUC, Precision-Recall curves, confusion matrices, and inference latency gauges.
5. **System Audit Logs:** Searchable immutable event stream of administrative and freeze actions.
