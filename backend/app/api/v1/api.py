from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth

api_router = APIRouter()

# Mount feature endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & RBAC"])

@api_router.get("/info", tags=["System"])
def get_system_info():
    return {
        "name": "upay Pulse API",
        "version": "1.0.0",
        "pillars": ["SecurityAI", "CustomerAI", "AgentAI"],
        "status": "operational"
    }
