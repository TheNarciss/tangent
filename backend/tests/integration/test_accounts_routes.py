"""Integration tests for /accounts routes (Phase A3, ADR-008)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.aggregator import AccountType
from app.aggregator import BankAccount as BankAccountDTO
from app.db.engine import async_session_factory
from app.db.models import BankAccount
from app.repositories import bank_accounts as accounts_repo


async def _register_login_and_get_id(client, email: str, password: str) -> tuple[str, uuid.UUID]:
    """Helper: register + login a user; return (auth cookie, user_id)."""
    from app.auth.models import User

    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    assert resp.status_code in (200, 201)

    resp = await client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 204
    cookie = resp.cookies.get("tangent_auth")
    assert cookie
    client.cookies.clear()

    async with async_session_factory() as session:
        res = await session.execute(select(User).where(User.email == email))
        user = res.scalars().first()
        assert user is not None
        return cookie, user.id


@pytest.mark.integration
async def test_list_accounts_empty_for_new_user(client):
    run_id = uuid.uuid4().hex[:8]
    cookie, user_id = await _register_login_and_get_id(
        client, f"empty-{run_id}@test.com", "TestPwd123!"
    )
    try:
        client.cookies.clear()
        resp = await client.get("/api/accounts", cookies={"tangent_auth": cookie})
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        async with async_session_factory() as session:
            await session.execute(
                BankAccount.__table__.delete().where(BankAccount.user_id == user_id)
            )
            await session.commit()


@pytest.mark.integration
async def test_list_accounts_isolation(client):
    """User A's accounts must NOT appear in User B's /accounts response."""
    run_id = uuid.uuid4().hex[:8]
    cookie_a, user_a = await _register_login_and_get_id(
        client, f"alice-r-{run_id}@test.com", "TestPwd123!"
    )
    cookie_b, user_b = await _register_login_and_get_id(
        client, f"bob-r-{run_id}@test.com", "TestPwd123!"
    )
    try:
        # Seed A
        async with async_session_factory() as session:
            await accounts_repo.upsert_account(
                session,
                user_a,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="route-A",
                    name="PEA Alice",
                    type=AccountType.PEA,
                    currency="EUR",
                    balance=8000.0,
                ),
            )

        # A sees their account
        client.cookies.clear()
        resp_a = await client.get("/api/accounts", cookies={"tangent_auth": cookie_a})
        assert resp_a.status_code == 200
        accounts_a = resp_a.json()
        assert len(accounts_a) == 1
        assert accounts_a[0]["name"] == "PEA Alice"

        # B sees nothing
        client.cookies.clear()
        resp_b = await client.get("/api/accounts", cookies={"tangent_auth": cookie_b})
        assert resp_b.status_code == 200
        assert resp_b.json() == []
    finally:
        async with async_session_factory() as session:
            await session.execute(
                BankAccount.__table__.delete().where(BankAccount.user_id.in_([user_a, user_b]))
            )
            await session.commit()


@pytest.mark.integration
async def test_get_account_404_for_other_users_account(client):
    """User B requesting User A's account_id must get 404 (not 403, to avoid info leak)."""
    run_id = uuid.uuid4().hex[:8]
    _cookie_a, user_a = await _register_login_and_get_id(
        client, f"alice-x-{run_id}@test.com", "TestPwd123!"
    )
    cookie_b, user_b = await _register_login_and_get_id(
        client, f"bob-x-{run_id}@test.com", "TestPwd123!"
    )
    try:
        # Seed A
        async with async_session_factory() as session:
            orm = await accounts_repo.upsert_account(
                session,
                user_a,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="x-A",
                    name="Hidden",
                    type=AccountType.CHECKING,
                    currency="EUR",
                    balance=100.0,
                ),
            )
            account_id = orm.id

        client.cookies.clear()
        resp = await client.get(f"/api/accounts/{account_id}", cookies={"tangent_auth": cookie_b})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    finally:
        async with async_session_factory() as session:
            await session.execute(
                BankAccount.__table__.delete().where(BankAccount.user_id.in_([user_a, user_b]))
            )
            await session.commit()


@pytest.mark.integration
async def test_sync_without_powens_credential_returns_400(client):
    run_id = uuid.uuid4().hex[:8]
    cookie, _user_id = await _register_login_and_get_id(
        client, f"nosync-{run_id}@test.com", "TestPwd123!"
    )
    try:
        client.cookies.clear()
        resp = await client.post("/api/accounts/sync", cookies={"tangent_auth": cookie})
        assert resp.status_code == 400
        assert "Powens" in resp.json()["detail"]
    finally:
        pass  # no DB cleanup needed (no rows created)
