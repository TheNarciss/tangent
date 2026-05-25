"""Multi-tenant isolation tests for Powens sync state (ADR-002, ADR-019).

Validates that user A cannot see user B's Powens sync metadata.
Required by ADR-002 as "non-négociable".
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.db.engine import async_session_factory
from app.db.models import PowensCredential


async def _register_and_login(client, email: str, password: str) -> str:
    """Register + login a user. Returns the auth cookie value (and clears client jar)."""
    client.cookies.clear()  # avoid stale cookies from previous logins

    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    assert resp.status_code in (200, 201), f"Register failed: {resp.text}"

    resp = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 204, f"Login failed: {resp.text}"

    cookie_value = resp.cookies.get("tangent_auth")
    assert cookie_value, f"No tangent_auth cookie after login: {dict(resp.cookies)}"

    # Clear client jar so subsequent register/login don't carry the cookie
    client.cookies.clear()
    return cookie_value


async def _user_id_for_email(email: str) -> uuid.UUID:
    from app.auth.models import User

    async with async_session_factory() as session:
        stmt = select(User).where(User.email == email)
        res = await session.execute(stmt)
        user = res.scalars().first()
        assert user is not None, f"No user with email={email}"
        return user.id


@pytest.mark.integration
async def test_sync_status_isolation_between_users(client):
    """User A's PowensCredential state must NOT leak to User B (ADR-002, ADR-019).

    Scenario:
    - User A: last_positions_count=100, cash_balance=500
    - User B: last_positions_count=200, cash_balance=1000
    - Each user's /sync/status must return their own state only.
    """
    run_id = uuid.uuid4().hex[:8]
    email_a = f"alice-iso-{run_id}@test.com"
    email_b = f"bob-iso-{run_id}@test.com"
    password = "TestPassword123!"

    token_a = await _register_and_login(client, email_a, password)
    token_b = await _register_and_login(client, email_b, password)

    user_a_id = await _user_id_for_email(email_a)
    user_b_id = await _user_id_for_email(email_b)
    assert user_a_id != user_b_id, "Test bug: same user_id for both users"

    # Seed different sync state for each user
    async with async_session_factory() as session:
        session.add_all(
            [
                PowensCredential(
                    user_id=user_a_id,
                    encrypted_token="dummy-A",
                    last_positions_count=100,
                    last_cash_balance=500.0,
                ),
                PowensCredential(
                    user_id=user_b_id,
                    encrypted_token="dummy-B",
                    last_positions_count=200,
                    last_cash_balance=1000.0,
                ),
            ]
        )
        await session.commit()

    try:
        # ── User A sees only their state ───────────────────────────────────
        client.cookies.clear()
        resp_a = await client.get("/sync/status", cookies={"tangent_auth": token_a})
        assert resp_a.status_code == 200, f"User A /sync/status: {resp_a.text}"
        data_a = resp_a.json()
        assert data_a["user_connected"] is True
        assert data_a["positions_count"] == 100, (
            f"❌ LEAK! User A got positions_count={data_a['positions_count']}, "
            f"expected 100 (User B's value is 200)"
        )
        assert data_a["cash_balance"] == 500.0

        # ── User B sees only their state ───────────────────────────────────
        client.cookies.clear()
        resp_b = await client.get("/sync/status", cookies={"tangent_auth": token_b})
        assert resp_b.status_code == 200, f"User B /sync/status: {resp_b.text}"
        data_b = resp_b.json()
        assert data_b["user_connected"] is True
        assert data_b["positions_count"] == 200, (
            f"❌ LEAK! User B got positions_count={data_b['positions_count']}, "
            f"expected 200 (User A's value is 100)"
        )
        assert data_b["cash_balance"] == 1000.0

    finally:
        # Cleanup (shared DB, no rollback between tests)
        async with async_session_factory() as session:
            await session.execute(
                PowensCredential.__table__.delete().where(
                    PowensCredential.user_id.in_([user_a_id, user_b_id])
                )
            )
            await session.commit()


@pytest.mark.integration
async def test_unauthenticated_sync_status_returns_401(client):
    """Sanity check: /sync/status without auth must be 401, not leak data."""
    client.cookies.clear()
    resp = await client.get("/sync/status")
    assert resp.status_code == 401
