"""Shared test fixtures.

Env vars set BEFORE app import.
Integration tests use httpx.AsyncClient (ASGI) with session-scoped event loop
to avoid asyncpg/BaseHTTPMiddleware cleanup issues.
"""
import os

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production-use-only")
os.environ.setdefault("RESET_TOKEN_SECRET", "test-reset-secret-not-for-production")
os.environ.setdefault(
    "POWENS_TOKEN_ENCRYPTION_KEY",
    "JzPK9Z-AjUYY4i_aQB9OBSqz_LIBOX6r4l5MmYFlBog=",
)
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://tangent:tangent_dev@localhost:5432/tangent",
)
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def client():
    """Session-scoped async client to share the same event loop across tests."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
