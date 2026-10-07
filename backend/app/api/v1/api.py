from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth, transactions, risk, freeze, scams, graph, customer_ai, agent_ai, soundbox, badge, events_ws, appeals, evidence, governance, security

api_router = APIRouter()

# Mount feature endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & RBAC"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions & Ledger"])
api_router.include_router(risk.router, prefix="/risk", tags=["SecurityAI: Risk Engine"])
api_router.include_router(freeze.router, prefix="/freeze", tags=["SecurityAI: Master Freeze"])
api_router.include_router(scams.router, prefix="/scams", tags=["SecurityAI: Citizen Scam Reporting"])
api_router.include_router(appeals.router, prefix="/appeals", tags=["SecurityAI: Citizen False-Positive Appeals"])
api_router.include_router(graph.router, prefix="/graph", tags=["SecurityAI: Money-Mule Graph Intelligence"])
api_router.include_router(customer_ai.router, prefix="/customer-ai", tags=["CustomerAI: Financial Intelligence"])
api_router.include_router(agent_ai.router, prefix="/agent-ai", tags=["AgentAI: Liquidity Intelligence"])
api_router.include_router(soundbox.router, prefix="/soundbox", tags=["AgentAI: Software Soundbox"])
api_router.include_router(badge.router, prefix="/badge", tags=["SecurityAI: Dynamic Anti-Screenshot Badge"])
api_router.include_router(events_ws.router, prefix="/events", tags=["Real-Time WebSockets & Event Bus"])
# Phase-2 governance, evidence dashboard, and live attack suite
api_router.include_router(evidence.router, prefix="/evidence", tags=["Phase-2: Evidence & Benchmarks"])
api_router.include_router(governance.router, prefix="/governance", tags=["Phase-2: Model Governance"])
api_router.include_router(security.router, prefix="/security", tags=["Phase-2: Security Attack Suite"])

@api_router.get("/info", tags=["System"])
def get_system_info():
    return {
        "name": "upay Pulse API",
        "version": "1.0.0",
        "pillars": ["SecurityAI", "CustomerAI", "AgentAI"],
        "status": "operational"
    }
