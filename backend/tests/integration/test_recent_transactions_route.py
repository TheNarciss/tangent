"""Integration test for GET /accounts/transactions/recent.

Validates:
- Returns transactions across ALL bank accounts of the user
- Ordered by transaction_date desc
- Includes bank_account_name (joined from BankAccount)
- Respects the `limit` query parameter
- Filters strictly by user_id (multi-tenant isolation)
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.aggregator import AccountType
from app.aggregator import BankAccount as BankAccountDTO
from app.db.engine import async_session_factory
from app.db.models import BankAccount, BankTransaction
from app.repositories import bank_accounts as accounts_repo


async def _register_login_and_get_id(client, email: str, password: str) -> tuple[str, uuid.UUID]:
    """Helper: register + login a user; return (auth cookie, user_id)."""
    from app.auth.models import User

    client.cookies.clear()
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    assert resp.status_code in (200, 201)

    resp = await client.post(
        "/auth/login",
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


async def _seed_account(user_id: uuid.UUID, *, name: str, suffix: str) -> uuid.UUID:
    """Create a bank account via the repo, return its id."""
    async with async_session_factory() as session:
        acc = await accounts_repo.upsert_account(
            session,
            user_id,
            BankAccountDTO(
                provider="powens",
                provider_account_id=f"recent-{suffix}",
                name=name,
                type=AccountType.CHECKING,
                currency="EUR",
                balance=0.0,
            ),
        )
        return acc.id


async def _seed_tx(
    user_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    *,
    amount: float,
    description: str,
    days_ago: int,
) -> None:
    async with async_session_factory() as session:
        session.add(
            BankTransaction(
                id=uuid.uuid4(),
                user_id=user_id,
                bank_account_id=bank_account_id,
                provider_transaction_id=f"tx-{uuid.uuid4().hex[:8]}",
                amount=amount,
                currency="EUR",
                transaction_date=date.today() - timedelta(days=days_ago),
                description=description,
                category=None,
            )
        )
        await session.commit()


async def _cleanup(user_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(
            BankTransaction.__table__.delete().where(BankTransaction.user_id == user_id)
        )
        await session.execute(
            BankAccount.__table__.delete().where(BankAccount.user_id == user_id)
        )
        await session.commit()


@pytest.mark.integration
async def test_recent_transactions_across_accounts_and_ordered(client):
    """Returns transactions across all accounts, ordered by date desc, with bank name."""
    run_id = uuid.uuid4().hex[:8]
    cookie, user_id = await _register_login_and_get_id(
        client, f"recent-{run_id}@test.com", "TestPwd123!"
    )
    try:
        acc1 = await _seed_account(user_id, name="Boursorama CC", suffix=f"{run_id}-a")
        acc2 = await _seed_account(user_id, name="Livret A", suffix=f"{run_id}-b")

        await _seed_tx(user_id, acc1, amount=-42.0, description="Carrefour", days_ago=1)
        await _seed_tx(user_id, acc1, amount=3000.0, description="Salaire", days_ago=5)
        await _seed_tx(user_id, acc2, amount=50.0, description="Interets", days_ago=2)

        client.cookies.clear()
        resp = await client.get(
            "/accounts/transactions/recent?limit=10",
            cookies={"tangent_auth": cookie},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3

        # Ordered by date desc: Carrefour (1d) > Interets (2d) > Salaire (5d)
        assert [t["description"] for t in body] == ["Carrefour", "Interets", "Salaire"]

        # bank_account_name joined
        assert body[0]["bank_account_name"] == "Boursorama CC"
        assert body[1]["bank_account_name"] == "Livret A"
        assert body[2]["bank_account_name"] == "Boursorama CC"

        # bank_account_type also joined
        assert body[0]["bank_account_type"] == "checking"
    finally:
        await _cleanup(user_id)


@pytest.mark.integration
async def test_recent_transactions_respects_limit(client):
    run_id = uuid.uuid4().hex[:8]
    cookie, user_id = await _register_login_and_get_id(
        client, f"recent-limit-{run_id}@test.com", "TestPwd123!"
    )
    try:
        acc = await _seed_account(user_id, name="Test", suffix=run_id)
        for i in range(5):
            await _seed_tx(user_id, acc, amount=-10.0, description=f"tx{i}", days_ago=i)

        client.cookies.clear()
        resp = await client.get(
            "/accounts/transactions/recent?limit=3",
            cookies={"tangent_auth": cookie},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 3
    finally:
        await _cleanup(user_id)


@pytest.mark.integration
async def test_recent_transactions_multi_tenant_isolation(client):
    """User A's transactions must NOT appear in User B's /recent response."""
    run_id = uuid.uuid4().hex[:8]
    cookie_a, user_a = await _register_login_and_get_id(
        client, f"recent-alice-{run_id}@test.com", "TestPwd123!"
    )
    cookie_b, user_b = await _register_login_and_get_id(
        client, f"recent-bob-{run_id}@test.com", "TestPwd123!"
    )
    try:
        acc_a = await _seed_account(user_a, name="Alice CC", suffix=f"{run_id}-a")
        acc_b = await _seed_account(user_b, name="Bob CC", suffix=f"{run_id}-b")

        await _seed_tx(user_a, acc_a, amount=-1.0, description="Alice spend", days_ago=0)
        await _seed_tx(user_b, acc_b, amount=-99.0, description="Bob spend", days_ago=0)

        # Bob fetches: should see only their own
        client.cookies.clear()
        resp = await client.get(
            "/accounts/transactions/recent?limit=10",
            cookies={"tangent_auth": cookie_b},
        )
        assert resp.status_code == 200
        descriptions = [t["description"] for t in resp.json()]
        assert "Bob spend" in descriptions
        assert "Alice spend" not in descriptions
    finally:
        await _cleanup(user_a)
        await _cleanup(user_b)
