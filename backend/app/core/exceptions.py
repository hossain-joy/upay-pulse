import logging
from datetime import datetime, timezone
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("upay_pulse.exceptions")

class AppException(Exception):
    def __init__(self, message: str, code: str = "BAD_REQUEST", status_code: int = 400, details: dict = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

async def app_exception_handler(request: Request, exc: AppException):
    logger.warning("Application exception on %s %s: [%s] %s", request.method, request.url.path, exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    formatted = []
    for err in errors:
        formatted.append({
            "field": ".".join(str(x) for x in err.get("loc", [])),
            "issue": err.get("msg")
        })
    logger.info("Validation failure on %s: %s", request.url.path, formatted)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The submitted payload contains invalid parameters.",
                "details": {"validation_errors": formatted},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail or "An HTTP error occurred.",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    # Log internal stack trace privately on the server
    logger.error("Unhandled internal exception on %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    # Return sanitized generic error message to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "We could not process your request at this time. Please try again shortly.",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )
