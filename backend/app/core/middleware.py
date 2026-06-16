"""Custom middleware for request correlation, error handling, and timing."""

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
