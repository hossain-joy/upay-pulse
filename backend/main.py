import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.config import settings
from backend.app.core.database import check_db_health
from backend.app.core.events import event_bus
from backend.app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler
)
from backend.app.api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("upay_pulse")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions — wrapped defensively so a transient failure in any
    # optional component does not prevent the API from becoming ready.
    # Render will otherwise mark the deploy as failed when uvicorn never
    # finishes startup.
    logger.info("Initializing upay Pulse API server (Version: %s)...", settings.VERSION)
    try:
        await event_bus.initialize()
    except Exception as e:
        logger.warning("EventBus init failed (continuing): %s", e)
    try:
        db_status = check_db_health()
        logger.info("Database health check: %s (%s)", db_status.get("status"), db_status.get("dialect"))
    except Exception as e:
        logger.warning("Database health check failed (continuing): %s", e)
    # Pre-warm Risk Model — best-effort; lazy-loaded on first request anyway.
    try:
        from backend.app.services.risk_scoring_service import RiskScoringService
        _ = RiskScoringService.get_model()
        logger.info("SecurityAI LightGBM model pre-warmed in memory.")
    except Exception as e:
        logger.warning("Risk model pre-warm failed (will lazy-load on first request): %s", e)
    yield
    # Shutdown actions
    logger.info("Shutting down upay Pulse API server...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered Mobile Financial Services (MFS) Intelligence Ecosystem",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Health & Observability Probes
@app.get("/health", tags=["Observability"])
def health_probe():
    """Liveness probe confirming API process responsiveness."""
    return {
        "status": "healthy",
        "service": "upay-pulse-backend",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/ready", tags=["Observability"])
def readiness_probe():
    """Readiness probe checking database and event bus readiness."""
    db_health = check_db_health()
    bus_health = event_bus.status()
    is_ready = db_health.get("status") == "healthy"
    
    return {
        "status": "ready" if is_ready else "not_ready",
        "database": db_health,
        "event_bus": bus_health
    }

@app.get("/", tags=["General"])
def root():
    return {
        "message": "Welcome to upay Pulse API — AI-powered MFS Intelligence Ecosystem",
        "docs": "/docs",
        "version": settings.VERSION,
        "mode": "Simulated MFS / Educational Hackathon Prototype"
    }

# Mount v1 API
app.include_router(api_router, prefix="/api/v1")
# Also mount api_router directly without prefix for seamless client compatibility
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
