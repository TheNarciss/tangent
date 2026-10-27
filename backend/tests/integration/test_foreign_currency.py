"""An account in Singapore dollars counts in euros, in totals and in spending (ADR-038)."""

from __future__ import annotations

import uuid
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import select

from app.aggregator import AccountType, Transaction
from app.aggregator import BankAccount as BankAccountDTO
from app.auth.models import User
from app.db.engine import async_session_factory
from app.deps import get_user_wealth
from app.errors import DataSourceError
from app.finance import fx
from app.repositories import bank_accounts as accounts_repo
from app.repositories import bank_transactions as txs_repo

SGD_PER_EUR = 1.5  # a round rate: 150 SGD = 100 €


@pytest.fixture(autouse=True)
def _ecb(monkeypatch):
    monkeypatch.setattr(fx, "_LAST_KNOWN", {})

    def series(key: str, *, start=None, last_n=None):
        if ".SGD." not in key:
            raise DataSourceError(f"{key} a répondu 404.")
        return pd.Series([SGD_PER_EUR], index=pd.to_datetime(["2026-10-26"]))

    monkeypatch.setattr(fx.ecb, "series", series)


async def _user() -> User:
    async with async_session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"fx-{uuid.uuid4().hex[:8]}@test.local",
            hashed_password="not-a-real-hash",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        return user


async def _drop(user_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        user = (await session.execute(select(User).where(User.id == user_id))).unique().scalar()
        if user:
            await session.delete(user)
            await session.commit()


def _account(pid: str, currency: str, balance: float, type_=AccountType.CHECKING):
    return BankAccountDTO(
        provider="finverse",
        provider_account_id=pid,
        institution_name="DBS",
        name=f"Compte {currency}",
        type=type_,
        balance=balance,
        currency=currency,
    )


def _debit(tx_id: str, pid: str, amount: float, currency: str) -> Transaction:
    return Transaction(
        provider="finverse",
        provider_transaction_id=tx_id,
        provider_account_id=pid,
        amount=amount,
        currency=currency,
        transaction_date=date.today(),
        description="KOPITIAM",
        category="alimentation",
    )


@pytest.mark.integration
async def test_balances_and_debts_in_sgd_count_in_euros():
    user = await _user()
    try:
        async with async_session_factory() as session:
            for dto in (
                _account("eur-1", "EUR", 1000.0),
                _account("sgd-1", "SGD", 1500.0),
                _account("sgd-loan", "SGD", -300.0, AccountType.LOAN),
                _account("vnd-1", "VND", 5_000_000.0),
            ):
                await accounts_repo.upsert_account(session, user.id, dto)
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        # 1000 € + 1500 SGD (1000 €); the VND account has no ECB rate: left out.
        assert wealth.checking_total == pytest.approx(2000.0)
        assert {a.provider_account_id for a in wealth.checking_accounts} == {"eur-1", "sgd-1"}
        assert wealth.total_liabilities == pytest.approx(200.0)
        assert all(a.currency == "EUR" for a in wealth.checking_accounts)
    finally:
        await _drop(user.id)


@pytest.mark.integration
async def test_spending_in_sgd_counts_in_euros():
    user = await _user()
    try:
        async with async_session_factory() as session:
            eur = await accounts_repo.upsert_account(session, user.id, _account("e", "EUR", 0))
            sgd = await accounts_repo.upsert_account(session, user.id, _account("s", "SGD", 0))
            await txs_repo.upsert_transactions(
                session, user.id, eur.id, [_debit("t-eur", "e", -30.0, "EUR")]
            )
            await txs_repo.upsert_transactions(
                session, user.id, sgd.id, [_debit("t-sgd", "s", -45.0, "SGD")]
            )
            await session.commit()

            since = date.today().replace(day=1)
            by_category = await txs_repo.spending_by_month_and_category(
                session, user.id, since=since
            )
            by_label = await txs_repo.spending_by_description(session, user.id, since=since)
            outflow = await txs_repo.monthly_outflow(session, user.id, days=30)

        # 30 € + 45 SGD (30 €), in one line per month and category.
        assert by_category == [(since, "alimentation", pytest.approx(60.0))]
        assert by_label == [("KOPITIAM", pytest.approx(60.0), 2)]
        assert outflow == pytest.approx(60.0 / (30 / 30.4375))
    finally:
        await _drop(user.id)
