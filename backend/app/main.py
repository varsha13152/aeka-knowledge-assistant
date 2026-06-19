"""AEKA Backend — FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import chat, documents, mcp_routes, metrics, review, search
from app.core.config import get_settings
from app.core.rate_limit import limiter

settings = get_settings()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.app_env == "development"
        else structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown hooks."""
    logger.info("Starting AEKA backend", env=settings.app_env)

    # Ensure storage bucket exists (idempotent)
    from app.services.storage import storage_service
    storage_service.ensure_bucket_exists()

    yield

    logger.info("Shutting down AEKA backend")


# ─── App Factory ────────────────────────────────────────────────────────────

app = FastAPI(
    title="AEKA — AI-Powered Enterprise Knowledge Assistant",
    description="Multi-agent RAG system with streaming responses and HITL workflows",
    version="0.1.0",
    lifespan=lifespan,
    # Disable API docs in non-development environments
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── Middleware ──────────────────────────────────────────────────────────────

from app.core.middleware import ErrorHandlerMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

# CORS: restrict origins to production frontend; allow localhost only in development
_cors_origins = [settings.frontend_url]
if settings.app_env == "development":
    _cors_origins.extend(["http://localhost:3000", "http://localhost:3002"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# ─── OpenTelemetry Instrumentation ─────────────────────────────────────────
# Disabled: FastAPI instrumentation has a bug with _IncludedRouter objects
# TODO: Re-enable after upgrading opentelemetry-instrumentation-fastapi
# if settings.app_env == "production":
#     from app.core.observability import instrument_app
#     instrument_app(app)

# ─── Routes ─────────────────────────────────────────────────────────────────

app.include_router(documents.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(mcp_routes.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "aeka-backend", "version": "0.1.0"}


@app.get("/")
async def root():
    """API root — redirect to docs."""
    return {
        "service": "AEKA Backend",
        "docs": "/docs",
        "health": "/health",
    }
