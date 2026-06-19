"""Shared test fixtures for pytest."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.auth import AuthenticatedUser


@pytest.fixture
def mock_user():
    """A mock authenticated user for testing."""
    return AuthenticatedUser(
        id="user_test123",
        email="test@example.com",
        full_name="Test User",
        role="student",
    )


@pytest.fixture
def mock_admin():
    """A mock admin user for testing."""
    return AuthenticatedUser(
        id="user_admin456",
        email="admin@example.com",
        full_name="Admin User",
        role="admin",
    )


@pytest.fixture
def override_auth(mock_user):
    """Override the auth dependency to return mock_user without real JWT."""
    from app.core.auth import get_current_user
    from app.main import app

    async def _mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = _mock_get_current_user
    yield mock_user
    app.dependency_overrides.clear()


@pytest.fixture
def override_admin_auth(mock_admin):
    """Override auth to return an admin user."""
    from app.core.auth import get_current_user
    from app.main import app

    async def _mock_get_current_user():
        return mock_admin

    app.dependency_overrides[get_current_user] = _mock_get_current_user
    yield mock_admin
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_auth):
    """Async test client with mocked auth."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def admin_client(override_admin_auth):
    """Async test client with admin auth."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
