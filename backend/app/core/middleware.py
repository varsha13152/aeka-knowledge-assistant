"""Custom middleware for request correlation, error handling, security headers, and timing."""

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.observability import request_id_ctx

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add a unique correlation ID to every request.

    - Generates X-Request-ID if not provided by client
    - Stores in contextvars for log correlation
    - Returns in response headers
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Use client-provided ID or generate one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request_id_ctx.set(request_id)

        # Bind to structlog for all logs in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Time the request
        start = time.perf_counter()

        response = await call_next(request)

        # Record duration
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        # Log request completion
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security response headers to all responses.

    Covers OWASP recommendations: clickjacking, MIME sniffing,
    strict transport, content security policy, and referrer leakage.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )

        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return structured error responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception("unhandled_error", error=str(exc))
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "request_id": request_id_ctx.get(""),
                    }
                },
            )
