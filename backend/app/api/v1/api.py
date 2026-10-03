from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth, transactions, risk, freeze, scams, graph, customer_ai, agent_ai

api_router = APIRouter()

# Mount feature endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & RBAC"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions & Ledger"])
api_router.include_router(risk.router, prefix="/risk", tags=["SecurityAI: Risk Engine"])
api_router.include_router(freeze.router, prefix="/freeze", tags=["SecurityAI: Master Freeze"])
api_router.include_router(scams.router, prefix="/scams", tags=["SecurityAI: Citizen Scam Reporting"])
api_router.include_router(graph.router, prefix="/graph", tags=["SecurityAI: Money-Mule Graph Intelligence"])
api_router.include_router(customer_ai.router, prefix="/customer-ai", tags=["CustomerAI: Financial Intelligence"])
api_router.include_router(agent_ai.router, prefix="/agent-ai", tags=["AgentAI: Liquidity Intelligence"])

@api_router.get("/info", tags=["System"])
def get_system_info():
    return {
        "name": "upay Pulse API",
        "version": "1.0.0",
        "pillars": ["SecurityAI", "CustomerAI", "AgentAI"],
        "status": "operational"
    }
