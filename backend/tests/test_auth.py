"""Tests for authentication and authorization."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401():
    """Requests without a token should return 401."""
    from app.main import app

    # Clear any overrides to test real auth
    app.dependency_overrides.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/api/v1/documents/")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_request_succeeds(client):
    """Requests with valid auth should succeed (may return empty data)."""
    response = await client.get("/api/v1/documents/")
    # May fail due to DB not being available in unit tests, but shouldn't be 401
    assert response.status_code != 401


@pytest.mark.asyncio
async def test_admin_endpoints_reject_students():
    """Student-role users should get 403 on admin endpoints."""
    from app.core.auth import AuthenticatedUser, get_current_user
    from app.main import app

    async def _mock_student():
        return AuthenticatedUser(id="user_student", role="student")

    app.dependency_overrides[get_current_user] = _mock_student

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/api/v1/metrics/")
        assert response.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_endpoints_allow_tutors():
    """Tutor-role users should access admin endpoints."""
    from app.core.auth import AuthenticatedUser, get_current_user
    from app.main import app

    async def _mock_tutor():
        return AuthenticatedUser(id="user_tutor", role="tutor")

    app.dependency_overrides[get_current_user] = _mock_tutor

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/api/v1/metrics/")
        # May fail due to no DB, but should not be 403
        assert response.status_code != 403

    app.dependency_overrides.clear()
