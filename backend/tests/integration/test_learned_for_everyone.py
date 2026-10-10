"""The nightly categorization starts from every user's history: it has to read the users.

From 16 September to 10 October 2026 it never got past that line: a whole
`User` row joins its OAuth accounts, and SQLAlchemy refuses to list such rows
without `.unique()`. Each night the gap-fill stopped there, before the LLM,
and every new merchant stayed without a category.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import date

import pytest
from sqlalchemy import select, update

from app.aggregator import AccountType, Transaction
from app.aggregator import BankAccount as BankAccountDTO
from app.auth.models import User
from app.db.engine import async_session_factory
from app.db.models import BankAccount, BankTransaction
from app.llm import batch_submitter
from app.repositories import bank_accounts as accounts_repo
from app.repositories import bank_transactions as txs_repo


async def _register(client, *, superuser: bool = False) -> tuple[str, uuid.UUID]:
    email = f"learned-{secrets.token_hex(4)}@test.com"
    pwd = "TestPwd123!"
    client.cookies.clear()
    resp = await client.post("/api/auth/register", json={"email": email, "password": pwd})
    assert resp.status_code in (200, 201), resp.text
    async with async_session_factory() as session:
        if superuser:
            await session.execute(update(User).where(User.email == email).values(is_superuser=True))
            await session.commit()
        user_id = (await session.execute(select(User.id).where(User.email == email))).scalar_one()
    await client.post("/api/auth/login", data={"username": email, "password": pwd})
    return email, user_id


async def _same_merchant_twice(user_id: uuid.UUID) -> None:
    """Once decided by the user, once still empty."""
    run = secrets.token_hex(4)
    async with async_session_factory() as session:
        acc = await accounts_repo.upsert_account(
            session,
            user_id,
            BankAccountDTO(
                provider="enablebanking",
                provider_account_id=f"acc-{run}",
                name="Revolut EUR",
                type=AccountType.CHECKING,
                currency="EUR",
                balance=50.0,
            ),
        )
        await txs_repo.upsert_transactions(
            session,
            user_id,
            acc.id,
            [
                Transaction(
                    provider="enablebanking",
                    provider_transaction_id=f"{run}-{day}",
                    provider_account_id=f"acc-{run}",
                    amount=-5.18,
                    currency="EUR",
                    transaction_date=date(2026, 10, day),
                    description="Starbucks@rochester(rp",
                    category=category,
                    category_source=source,
                )
                for day, category, source in [(4, "restaurant", "user"), (9, None, None)]
            ],
        )


async def _categories(user_id: uuid.UUID) -> list[tuple[str | None, str | None]]:
    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(BankTransaction.category, BankTransaction.category_source)
                .where(BankTransaction.user_id == user_id)
                .order_by(BankTransaction.transaction_date)
            )
        ).all()
    return [(category, source) for category, source in rows]


async def _cleanup(user_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(BankAccount.__table__.delete().where(BankAccount.user_id == user_id))
        await session.commit()


@pytest.mark.integration
async def test_the_night_applies_every_users_history_before_the_llm(client):
    _, user_id = await _register(client)
    try:
        await _same_merchant_twice(user_id)
        async with async_session_factory() as session:
            learned = await batch_submitter._apply_learned_for_everyone(session)
        assert learned >= 1
        assert await _categories(user_id) == [("restaurant", "user"), ("restaurant", "history")]
    finally:
        await _cleanup(user_id)


@pytest.mark.integration
async def test_the_admin_catch_up_and_user_list_read_every_user(client, monkeypatch):
    async def no_batch(session, *, gaps_only=False):
        return None

    monkeypatch.setattr(batch_submitter, "submit_nightly_batch", no_batch)
    email, user_id = await _register(client, superuser=True)
    try:
        await _same_merchant_twice(user_id)
        resp = await client.post("/api/admin/categorize")
        assert resp.status_code == 200, resp.text
        assert resp.json()["learned"] >= 1
        assert await _categories(user_id) == [("restaurant", "user"), ("restaurant", "history")]

        resp = await client.get("/api/admin/users")
        assert resp.status_code == 200, resp.text
        assert email in {u["email"] for u in resp.json()}
    finally:
        await _cleanup(user_id)
