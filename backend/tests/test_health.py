"""Tests for the health check endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_responds():
    """Health endpoint should respond without authentication."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "aeka-backend"
        assert "status" in data
        assert "checks" in data
        assert "postgres" in data["checks"]
        assert "redis" in data["checks"]
        assert "storage" in data["checks"]


@pytest.mark.asyncio
async def test_root_endpoint():
    """Root endpoint should return service info."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "AEKA Backend"
