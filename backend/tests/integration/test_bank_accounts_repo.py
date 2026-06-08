"""Multi-tenant isolation tests for bank_accounts / holdings / bank_transactions repos.

Validates ADR-002 (no cross-tenant leak) for the Phase A multi-account tables.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.aggregator import (
    AccountType,
    Investment,
    Transaction,
)
from app.aggregator import (
    BankAccount as BankAccountDTO,
)
from app.db.engine import async_session_factory
from app.db.models import BankAccount
from app.repositories import account_holdings as holdings_repo
from app.repositories import bank_accounts as accounts_repo
from app.repositories import bank_transactions as bank_txs_repo


async def _register_and_get_user_id(client, email: str, password: str) -> uuid.UUID:
    """Helper: register a user via API, fetch their id from DB."""
    from app.auth.models import User

    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    assert resp.status_code in (200, 201), f"Register failed: {resp.text}"
    client.cookies.clear()

    async with async_session_factory() as session:
        stmt = select(User).where(User.email == email)
        res = await session.execute(stmt)
        user = res.scalars().first()
        assert user is not None
        return user.id


async def _cleanup_user(user_id: uuid.UUID) -> None:
    """Cascade-delete all rows for a user."""
    async with async_session_factory() as session:
        await session.execute(BankAccount.__table__.delete().where(BankAccount.user_id == user_id))
        await session.commit()


@pytest.mark.integration
async def test_bank_accounts_isolation_between_users(client):
    """User A's bank account must NOT be visible to User B (ADR-002)."""
    run_id = uuid.uuid4().hex[:8]
    user_a = await _register_and_get_user_id(client, f"alice-ba-{run_id}@test.com", "TestPwd123!")
    user_b = await _register_and_get_user_id(client, f"bob-ba-{run_id}@test.com", "TestPwd123!")

    try:
        # Insert A's account
        async with async_session_factory() as session:
            await accounts_repo.upsert_account(
                session,
                user_a,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="acc-A-1",
                    name="PEA Alice",
                    type=AccountType.PEA,
                    currency="EUR",
                    balance=10000.0,
                ),
            )

        # A sees their account
        async with async_session_factory() as session:
            accounts_a = await accounts_repo.list_accounts(session, user_a)
            assert len(accounts_a) == 1
            assert accounts_a[0].name == "PEA Alice"

        # B sees NOTHING
        async with async_session_factory() as session:
            accounts_b = await accounts_repo.list_accounts(session, user_b)
            assert len(accounts_b) == 0, (
                f"❌ LEAK! User B got {len(accounts_b)} accounts (must be 0)"
            )

    finally:
        await _cleanup_user(user_a)
        await _cleanup_user(user_b)


@pytest.mark.integration
async def test_upsert_account_is_idempotent(client):
    """Re-upserting same (provider, provider_account_id) updates instead of duplicating."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"idem-{run_id}@test.com", "TestPwd123!")

    try:
        async with async_session_factory() as session:
            await accounts_repo.upsert_account(
                session,
                user_id,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="acc-X",
                    name="Original",
                    type=AccountType.CHECKING,
                    currency="EUR",
                    balance=500.0,
                ),
            )
            await accounts_repo.upsert_account(
                session,
                user_id,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="acc-X",  # same provider_account_id
                    name="Updated",
                    type=AccountType.CHECKING,
                    currency="EUR",
                    balance=750.0,
                ),
            )

            accounts = await accounts_repo.list_accounts(session, user_id)
            assert len(accounts) == 1, f"Expected 1 account, got {len(accounts)}"
            assert accounts[0].name == "Updated"
            assert accounts[0].balance == 750.0
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_replace_holdings_is_idempotent(client):
    """Calling replace_holdings twice with same data yields same DB state."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"hold-{run_id}@test.com", "TestPwd123!")

    try:
        async with async_session_factory() as session:
            acc = await accounts_repo.upsert_account(
                session,
                user_id,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="acc-H",
                    name="PEA Test",
                    type=AccountType.PEA,
                    currency="EUR",
                    balance=5000.0,
                ),
            )
            account_id = acc.id

            holdings = [
                Investment(
                    provider="powens",
                    provider_investment_id="inv-1",
                    provider_account_id="acc-H",
                    ticker="DCAM.PA",
                    label="Danone",
                    quantity=10,
                    unit_price=55.0,
                    current_value=580.0,
                    currency="EUR",
                ),
            ]

            await holdings_repo.replace_holdings(session, user_id, account_id, holdings)
            after_first = await holdings_repo.list_holdings(session, user_id, account_id)
            assert len(after_first) == 1

            # Replace again with same data → still 1 row, same content
            await holdings_repo.replace_holdings(session, user_id, account_id, holdings)
            after_second = await holdings_repo.list_holdings(session, user_id, account_id)
            assert len(after_second) == 1
            assert after_second[0].ticker == "DCAM.PA"
            assert after_second[0].quantity == 10.0
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_upsert_transactions_skips_duplicates(client):
    """Inserting same provider_transaction_id twice doesn't duplicate."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"txs-{run_id}@test.com", "TestPwd123!")

    try:
        async with async_session_factory() as session:
            acc = await accounts_repo.upsert_account(
                session,
                user_id,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="acc-T",
                    name="Checking Test",
                    type=AccountType.CHECKING,
                    currency="EUR",
                    balance=1000.0,
                ),
            )
            account_id = acc.id

            txs = [
                Transaction(
                    provider="powens",
                    provider_transaction_id="tx-1",
                    provider_account_id="acc-T",
                    amount=-42.50,
                    currency="EUR",
                    transaction_date=date(2026, 5, 20),
                    description="Carrefour",
                    category="Groceries",
                ),
                Transaction(
                    provider="powens",
                    provider_transaction_id="tx-2",
                    provider_account_id="acc-T",
                    amount=1000.0,
                    currency="EUR",
                    transaction_date=date(2026, 5, 1),
                    description="Salaire",
                ),
            ]

            inserted_1 = await bank_txs_repo.upsert_transactions(session, user_id, account_id, txs)
            assert inserted_1 == 2

            # Re-upsert same txs → 0 new
            inserted_2 = await bank_txs_repo.upsert_transactions(session, user_id, account_id, txs)
            assert inserted_2 == 0

            # List should still have 2
            listed = await bank_txs_repo.list_transactions(session, user_id, account_id)
            assert len(listed) == 2
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_replace_holdings_upserts_and_drops_orphans(client):
    """Second snapshot updates existing rows + removes vanished ones."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"hold2-{run_id}@test.com", "TestPwd123!")

    try:
        async with async_session_factory() as session:
            acc = await accounts_repo.upsert_account(
                session,
                user_id,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="acc-H2",
                    name="PEA Test 2",
                    type=AccountType.PEA,
                    currency="EUR",
                    balance=10_000.0,
                ),
            )
            account_id = acc.id

            snap1 = [
                Investment(
                    provider="powens",
                    provider_investment_id="inv-A",
                    provider_account_id="acc-H2",
                    ticker="DCAM.PA",
                    label="Danone",
                    quantity=10,
                    unit_price=55.0,
                    current_value=580.0,
                    currency="EUR",
                ),
                Investment(
                    provider="powens",
                    provider_investment_id="inv-B",
                    provider_account_id="acc-H2",
                    ticker="PUST.PA",
                    label="Amundi PEA S&P 500",
                    quantity=5,
                    unit_price=30.0,
                    current_value=160.0,
                    currency="EUR",
                ),
            ]
            await holdings_repo.replace_holdings(session, user_id, account_id, snap1)
            assert len(await holdings_repo.list_holdings(session, user_id, account_id)) == 2

            # Second snapshot: inv-A's quantity bumps, inv-B disappears, inv-C added.
            snap2 = [
                Investment(
                    provider="powens",
                    provider_investment_id="inv-A",
                    provider_account_id="acc-H2",
                    ticker="DCAM.PA",
                    label="Danone",
                    quantity=12,
                    unit_price=56.0,
                    current_value=720.0,
                    currency="EUR",
                ),
                Investment(
                    provider="powens",
                    provider_investment_id="inv-C",
                    provider_account_id="acc-H2",
                    ticker="ETZ.PA",
                    label="Amundi Euro Stoxx",
                    quantity=20,
                    unit_price=25.0,
                    current_value=510.0,
                    currency="EUR",
                ),
            ]
            await holdings_repo.replace_holdings(session, user_id, account_id, snap2)
            after = await holdings_repo.list_holdings(session, user_id, account_id)

            by_pid = {h.provider_investment_id: h for h in after}
            assert set(by_pid.keys()) == {"inv-A", "inv-C"}, "orphan inv-B should be gone"
            assert by_pid["inv-A"].quantity == 12.0, (
                "inv-A should have been updated, not duplicated"
            )
            assert by_pid["inv-A"].unit_price == 56.0
            assert by_pid["inv-C"].ticker == "ETZ.PA"

            # Third snapshot: empty list → all rows removed.
            await holdings_repo.replace_holdings(session, user_id, account_id, [])
            assert await holdings_repo.list_holdings(session, user_id, account_id) == []
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_list_and_get_account_exclude_soft_deleted(client):
    """list_accounts and get_account must skip rows flagged with powens_deleted_at."""
    from datetime import UTC, datetime

    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"sd-{run_id}@test.com", "TestPwd123!")

    try:
        async with async_session_factory() as session:
            kept = await accounts_repo.upsert_account(
                session,
                user_id,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="acc-keep",
                    name="Live account",
                    type=AccountType.CHECKING,
                    currency="EUR",
                    balance=1000.0,
                ),
            )
            soft_deleted = await accounts_repo.upsert_account(
                session,
                user_id,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id="acc-del",
                    name="Closed account",
                    type=AccountType.CHECKING,
                    currency="EUR",
                    balance=0.0,
                    powens_deleted_at=datetime(2026, 5, 30, tzinfo=UTC),
                ),
            )

            listed = await accounts_repo.list_accounts(session, user_id)
            listed_ids = {a.id for a in listed}
            assert kept.id in listed_ids, "live account should appear in list"
            assert soft_deleted.id not in listed_ids, "soft-deleted account must be hidden"

            assert await accounts_repo.get_account(session, user_id, kept.id) is not None
            assert await accounts_repo.get_account(session, user_id, soft_deleted.id) is None, (
                "get_account on a soft-deleted row must return None (→ route renders 404)"
            )
    finally:
        await _cleanup_user(user_id)
