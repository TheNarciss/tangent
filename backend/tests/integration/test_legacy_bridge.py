"""Integration tests for the legacy Portfolio bridge inside /accounts/sync.

The bridge derives legacy Position rows from the multi-account sync result
so that dashboard/historique/optimisation tabs (which still read from the
legacy model) keep working through the Phase A transition.

We test the bridge function directly (no Powens HTTP mocking required).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.aggregator import AccountType, BankAccount, Investment, SyncResult
from app.auth.models import User
from app.db.engine import async_session_factory
from app.db.models import Portfolio, Position
from app.repositories import portfolio as portfolio_repo
from app.routers.accounts import _sync_to_legacy_portfolio


async def _create_test_user() -> uuid.UUID:
    """Create a minimal valid user in DB so FK constraints pass."""
    user_id = uuid.uuid4()
    async with async_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=f"bridge-{user_id.hex[:8]}@test.local",
                hashed_password="not-a-real-hash",
                is_active=True,
                is_superuser=False,
                is_verified=False,
            )
        )
        await session.commit()
    return user_id


def _inv(
    provider_account_id: str,
    provider_investment_id: str,
    ticker: str,
    quantity: float,
    unit_price: float,
    current_value: float,
    isin: str = "FR0000000000",
    label: str | None = None,
) -> Investment:
    return Investment(
        provider="powens",
        provider_investment_id=provider_investment_id,
        provider_account_id=provider_account_id,
        ticker=ticker,
        isin=isin,
        label=label or ticker,
        quantity=quantity,
        unit_price=unit_price,
        current_value=current_value,
        currency="EUR",
    )


def _acc(provider_account_id: str, name: str, type_: AccountType, balance: float) -> BankAccount:
    return BankAccount(
        provider="powens",
        provider_account_id=provider_account_id,
        name=name,
        type=type_,
        currency="EUR",
        balance=balance,
    )


def _sync_result(
    accounts: list[BankAccount],
    investments: list[Investment],
) -> SyncResult:
    return SyncResult(
        success=True,
        provider="powens",
        accounts=accounts,
        investments=investments,
        transactions=[],
        synced_at=datetime.now(timezone.utc),
    )


@pytest.mark.integration
async def test_bridge_aggregates_holdings_by_ticker_across_accounts():
    user_id = await _create_test_user()
    try:
        accounts = [
            _acc("pea-1", "PEA Titres", AccountType.PEA, 10000.0),
            _acc("cto-1", "CTO", AccountType.CTO, 5000.0),
        ]
        investments = [
            _inv("pea-1", "inv-pea-1", "CW8.PA", 10.0, 80.0, 900.0),
            _inv("cto-1", "inv-cto-1", "CW8.PA", 5.0, 100.0, 450.0),
        ]
        result = _sync_result(accounts, investments)

        async with async_session_factory() as session:
            count = await _sync_to_legacy_portfolio(session, user_id, result)
            assert count == 1

        async with async_session_factory() as session:
            portfolio = await portfolio_repo.get_or_create(session, user_id)
            await session.refresh(portfolio, attribute_names=["positions"])
            assert len(portfolio.positions) == 1
            pos = portfolio.positions[0]
            assert pos.ticker == "CW8.PA"
            assert pos.quantity == 15.0
            assert abs(pos.avg_cost - 86.6667) < 0.01
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_bridge_sums_pea_cash_accounts_into_legacy_cash():
    user_id = await _create_test_user()
    try:
        accounts = [
            _acc("pea-titres", "PEA Titres", AccountType.PEA, 10000.0),
            _acc("pea-espece-bnp", "PEA Espèces", AccountType.PEA, 250.50),
            _acc("pea-cash-bp", "PEA Cash BP", AccountType.PEA, 100.00),
        ]
        result = _sync_result(accounts, investments=[])

        async with async_session_factory() as session:
            await _sync_to_legacy_portfolio(session, user_id, result)

        async with async_session_factory() as session:
            portfolio = await portfolio_repo.get_or_create(session, user_id)
            assert portfolio.cash == 350.50
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_bridge_idempotent_overwrites_stale_positions():
    user_id = await _create_test_user()
    try:
        accounts = [_acc("pea-1", "PEA", AccountType.PEA, 1000.0)]

        result1 = _sync_result(
            accounts,
            [_inv("pea-1", "inv-old", "OLD.PA", 1.0, 10.0, 10.0)],
        )
        async with async_session_factory() as session:
            await _sync_to_legacy_portfolio(session, user_id, result1)

        result2 = _sync_result(
            accounts,
            [_inv("pea-1", "inv-new", "NEW.PA", 2.0, 50.0, 100.0)],
        )
        async with async_session_factory() as session:
            await _sync_to_legacy_portfolio(session, user_id, result2)

        async with async_session_factory() as session:
            portfolio = await portfolio_repo.get_or_create(session, user_id)
            await session.refresh(portfolio, attribute_names=["positions"])
            assert len(portfolio.positions) == 1
            assert portfolio.positions[0].ticker == "NEW.PA"
    finally:
        await _cleanup_user(user_id)

@pytest.mark.integration
async def test_bridge_replaces_positions_with_same_ticker():
    """Regression: 2nd sync with same ticker as 1st must not violate uq constraint."""
    user_id = await _create_test_user()
    try:
        accounts = [_acc("pea-1", "PEA", AccountType.PEA, 1000.0)]

        # 1st sync — DCAM.PA at quantity 41
        result1 = _sync_result(
            accounts,
            [_inv("pea-1", "inv-1", "DCAM.PA", 41.0, 5.53, 250.0)],
        )
        async with async_session_factory() as session:
            await _sync_to_legacy_portfolio(session, user_id, result1)

        # 2nd sync — same DCAM.PA but different quantity (user bought more)
        result2 = _sync_result(
            accounts,
            [_inv("pea-1", "inv-1", "DCAM.PA", 50.0, 5.60, 300.0)],
        )
        async with async_session_factory() as session:
            # This used to crash with UniqueViolationError before the flush() fix
            await _sync_to_legacy_portfolio(session, user_id, result2)

        async with async_session_factory() as session:
            portfolio = await portfolio_repo.get_or_create(session, user_id)
            await session.refresh(portfolio, attribute_names=["positions"])
            assert len(portfolio.positions) == 1
            assert portfolio.positions[0].quantity == 50.0
    finally:
        await _cleanup_user(user_id)
@pytest.mark.integration
async def test_bridge_skips_zero_quantity_holdings():
    user_id = await _create_test_user()
    try:
        accounts = [_acc("pea-1", "PEA", AccountType.PEA, 0.0)]
        investments = [
            _inv("pea-1", "inv-alive", "ALIVE.PA", 5.0, 100.0, 500.0),
            _inv("pea-1", "inv-dead", "DEAD.PA", 0.0, 0.0, 0.0),
        ]
        result = _sync_result(accounts, investments)

        async with async_session_factory() as session:
            count = await _sync_to_legacy_portfolio(session, user_id, result)
            assert count == 1

        async with async_session_factory() as session:
            portfolio = await portfolio_repo.get_or_create(session, user_id)
            await session.refresh(portfolio, attribute_names=["positions"])
            assert len(portfolio.positions) == 1
            assert portfolio.positions[0].ticker == "ALIVE.PA"
    finally:
        await _cleanup_user(user_id)


async def _cleanup_user(user_id: uuid.UUID) -> None:
    """Wipe portfolio + positions + user created during the test."""
    async with async_session_factory() as session:
        res = await session.execute(select(Portfolio).where(Portfolio.user_id == user_id))
        portfolio = res.scalar_one_or_none()
        if portfolio is not None:
            await session.execute(
                Position.__table__.delete().where(Position.portfolio_id == portfolio.id)
            )
            await session.execute(
                Portfolio.__table__.delete().where(Portfolio.id == portfolio.id)
            )
        await session.execute(User.__table__.delete().where(User.id == user_id))
        await session.commit()
