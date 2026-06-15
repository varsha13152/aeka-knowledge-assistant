"""AEKA Backend — FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, search
from app.core.config import get_settings

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

    # Create S3 bucket if it doesn't exist (for local dev with MinIO)
    if settings.app_env == "development":
        try:
            import boto3

            s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.aws_region,
            )
            try:
                s3.head_bucket(Bucket=settings.s3_bucket_name)
            except Exception:
                s3.create_bucket(Bucket=settings.s3_bucket_name)
                logger.info("Created S3 bucket", bucket=settings.s3_bucket_name)
        except Exception as e:
            logger.warning("Could not initialize S3 bucket", error=str(e))

    yield

    logger.info("Shutting down AEKA backend")


# ─── App Factory ────────────────────────────────────────────────────────────

app = FastAPI(
    title="AEKA — AI-Powered Enterprise Knowledge Assistant",
    description="Multi-agent RAG system with streaming responses and HITL workflows",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ─────────────────────────────────────────────────────────────────

app.include_router(documents.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


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
