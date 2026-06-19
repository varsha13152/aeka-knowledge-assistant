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

# ─── Sentry Error Monitoring ──────────────────────────────────────────────
if settings.sentry_dsn:
    import sentry_sdk
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=0.1 if settings.app_env == "production" else 1.0,
        profiles_sample_rate=0.1 if settings.app_env == "production" else 0.0,
    )

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

    # Validate Clerk configuration
    if settings.app_env != "development" and not settings.clerk_jwks_url:
        raise RuntimeError(
            "FATAL: CLERK_JWKS_URL not configured. "
            "Set it to https://<your-clerk-domain>/.well-known/jwks.json"
        )

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
    """Health check endpoint for container orchestration.

    Pings all external dependencies and reports degraded status if any are down.
    """
    checks: dict[str, str] = {}

    # Check PostgreSQL
    try:
        from app.db.session import async_session_factory
        from sqlalchemy import text as sa_text

        async with async_session_factory() as db:
            await db.execute(sa_text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "down"

    # Check Redis
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "down"

    # Check R2 (storage)
    try:
        from app.services.storage import storage_service

        storage_service._client.head_bucket(Bucket=storage_service.bucket)
        checks["storage"] = "ok"
    except Exception:
        checks["storage"] = "down"

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "service": "aeka-backend",
        "version": "0.1.0",
        "checks": checks,
    }


@app.get("/")
async def root():
    """API root — redirect to docs."""
    return {
        "service": "AEKA Backend",
        "docs": "/docs",
        "health": "/health",
    }
