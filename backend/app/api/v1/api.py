from fastapi import APIRouter

api_router = APIRouter()

@api_router.get("/info", tags=["System"])
def get_system_info():
    return {
        "name": "upay Pulse API",
        "version": "1.0.0",
        "pillars": ["SecurityAI", "CustomerAI", "AgentAI"],
        "status": "operational"
    }
