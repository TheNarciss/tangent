"""Shared test fixtures.

Env vars set BEFORE app import. Integration tests use httpx.AsyncClient
(ASGI). ASGITransport doesn't trigger startup events, so we explicitly
apply Alembic migrations in the fixture — same mechanism as production
(`alembic upgrade head` via init_db).
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
# Test-only Fernet key — generated at session start to avoid hardcoded
# secrets triggering gitleaks (cf ADR-014 §5).
from cryptography.fernet import Fernet as _Fernet  # noqa: E402
os.environ.setdefault("OAUTH_TOKEN_ENCRYPTION_KEY", _Fernet.generate_key().decode())
os.environ.setdefault("OAUTH_STATE_SECRET", "test-oauth-state-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET", "test-google-client-secret")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def client():
    """Session-scoped async client. Runs Alembic migrations before yielding."""
    from app.db.init_db import init_db
    from app.main import app

    # Same mechanism as production lifespan: alembic upgrade head.
    # On a fresh CI DB, this creates the 8 tables + alembic_version.
    # On a dev DB already stamped at head, this is a no-op.
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def _reset_auth_rate_limits():
    """Wipe in-memory rate-limit counters before each test.

    Without this, the 3/hour register limit (cf ADR-011) blocks any test suite
    that creates more than 3 users via /auth/register on the same client IP.
    """
    from app.main import _attempts

    _attempts.clear()
    yield
