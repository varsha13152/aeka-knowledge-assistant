# ─── Stage 1: Dependencies ──────────────────────────────────────────────────
FROM python:3.12-slim AS dependencies

WORKDIR /app

# Install system deps for asyncpg and document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Copy full source for install (hatchling needs it for metadata)
COPY pyproject.toml .
COPY app/__init__.py app/__init__.py

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[dev]"

# ─── Stage 2: Production ───────────────────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos "" appuser

COPY --chown=appuser:appuser --from=dependencies /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=appuser:appuser --from=dependencies /usr/local/bin /usr/local/bin

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ─── Stage 3: Development (with hot reload) ────────────────────────────────
FROM dependencies AS development

RUN adduser --disabled-password --gecos "" devuser
COPY --chown=devuser:devuser . .
USER devuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
