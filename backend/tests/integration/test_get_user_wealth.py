"""Integration test: get_user_wealth builds correct Wealth from bank_accounts."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.aggregator import AccountType, Investment
from app.aggregator import BankAccount as BankAccountDTO
from app.auth.models import User
from app.db.engine import async_session_factory
from app.deps import get_user_wealth
from app.repositories import account_holdings as holdings_repo
from app.repositories import bank_accounts as accounts_repo


async def _create_test_user() -> User:
    """Create a minimal valid user in DB."""
    user_id = uuid.uuid4()
    async with async_session_factory() as session:
        user = User(
            id=user_id,
            email=f"wealth-{user_id.hex[:8]}@test.local",
            hashed_password="not-a-real-hash",
            is_active=True,
            is_superuser=False,
            is_verified=False,
        )
        session.add(user)
        await session.commit()
        return user


async def _cleanup_user(user_id: uuid.UUID) -> None:
    """Delete user + cascade (bank_accounts/holdings via FK)."""
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        # .unique() required because User eager-loads oauth_accounts collection
        user = result.unique().scalar_one_or_none()
        if user:
            await session.delete(user)
            await session.commit()


def _bank_dto(
    provider_account_id: str,
    type_: AccountType,
    name: str,
    balance: float,
    *,
    institution: str = "Test Bank",
    raw_data: dict | None = None,
) -> BankAccountDTO:
    return BankAccountDTO(
        provider="powens",
        provider_account_id=provider_account_id,
        institution_name=institution,
        name=name,
        type=type_,
        balance=balance,
        valuation=None,
        currency="EUR",
        raw_data=raw_data or {},
    )


@pytest.mark.integration
async def test_wealth_classifies_checking_account():
    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            await accounts_repo.upsert_account(
                session,
                user.id,
                _bank_dto("c-1", AccountType.CHECKING, "Compte courant", 2000.0),
            )
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        assert len(wealth.checking_accounts) == 1
        assert wealth.checking_accounts[0].balance == 2000.0
        assert wealth.checking_total == 2000.0
        assert wealth.envelopes == []
        assert wealth.investment_accounts == []
    finally:
        await _cleanup_user(user.id)


@pytest.mark.integration
async def test_wealth_treats_savings_as_checking():
    """Non-regulated SAVINGS are merged into checking (mobile cash)."""
    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            await accounts_repo.upsert_account(
                session,
                user.id,
                _bank_dto("s-1", AccountType.SAVINGS, "Hello! Plus", 5000.0),
            )
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        assert wealth.checking_total == 5000.0
        assert wealth.envelopes == []
    finally:
        await _cleanup_user(user.id)


@pytest.mark.integration
async def test_wealth_classifies_envelope_with_yaml_metadata():
    """Livret A is enriched with rate + ceiling from envelopes.yaml."""
    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            await accounts_repo.upsert_account(
                session,
                user.id,
                _bank_dto("la-1", AccountType.LIVRET_A, "Livret A", 15000.0),
            )
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        assert len(wealth.envelopes) == 1
        env = wealth.envelopes[0]
        assert env.balance == 15000.0
        assert env.envelope_type == "livret_a"
        # Metadata enriched from envelopes.yaml
        assert env.rate_pct is not None
        assert env.ceiling_eur is not None
        assert env.display_name is not None
        assert env.headroom_eur is not None
    finally:
        await _cleanup_user(user.id)


@pytest.mark.integration
async def test_wealth_classifies_pea_with_holdings_as_investment():
    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            acc_dto = _bank_dto("pea-titres", AccountType.PEA, "PEA Titres", 5000.0)
            acc_db = await accounts_repo.upsert_account(session, user.id, acc_dto)
            await holdings_repo.replace_holdings(
                session,
                user.id,
                acc_db.id,
                [
                    Investment(
                        provider="powens",
                        provider_investment_id="inv-1",
                        provider_account_id="pea-titres",
                        ticker="WPEA.PA",
                        label="iShares MSCI World",
                        quantity=10.0,
                        unit_price=50.0,
                        current_value=550.0,
                        currency="EUR",
                    ),
                ],
            )
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        assert len(wealth.investment_accounts) == 1
        assert wealth.pea_cash_accounts == []
        inv_acc = wealth.investment_accounts[0]
        assert inv_acc.account_type == "pea"
        assert len(inv_acc.positions) == 1
        assert inv_acc.positions[0].ticker == "WPEA.PA"
        assert inv_acc.positions_value == 550.0
        assert inv_acc.unrealized_pnl == 50.0  # 550 - 10*50
    finally:
        await _cleanup_user(user.id)


@pytest.mark.integration
async def test_wealth_classifies_pea_without_holdings_as_pea_cash():
    """PEA sub-account with 0 holdings → pea_cash_accounts (structural detection)."""
    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            await accounts_repo.upsert_account(
                session,
                user.id,
                _bank_dto("pea-espece", AccountType.PEA, "PEA Espèces", 100.0),
            )
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        assert wealth.investment_accounts == []
        assert len(wealth.pea_cash_accounts) == 1
        assert wealth.pea_cash_accounts[0].is_pea_cash is True
        assert wealth.pea_cash_total == 100.0
    finally:
        await _cleanup_user(user.id)


@pytest.mark.integration
async def test_wealth_classifies_loan_normalized_positive():
    """Powens loans have negative balance; Wealth stores positive outstanding."""
    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            await accounts_repo.upsert_account(
                session,
                user.id,
                _bank_dto(
                    "loan-1",
                    AccountType.LOAN,
                    "Prêt étudiant",
                    -30000.0,
                    raw_data={
                        "loan": {
                            "rate": 1.5,  # 1.5% in Powens "percent" format
                            "next_payment_amount": 250.0,
                            "next_payment_date": "2027-09-01",
                            "deferred_until": "2027-09-01",
                            "maturity_date": "2035-09-01",
                        }
                    },
                ),
            )
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        assert len(wealth.loans) == 1
        loan = wealth.loans[0]
        assert loan.outstanding_balance == 30000.0  # positive
        assert loan.interest_rate_pct == 0.015  # 1.5% → 0.015 decimal
        assert loan.monthly_payment == 250.0
        assert loan.maturity_date is not None
        assert wealth.total_liabilities == 30000.0
        assert wealth.net_worth == -30000.0
    finally:
        await _cleanup_user(user.id)


@pytest.mark.integration
async def test_wealth_full_scenario_matches_real_user():
    """End-to-end : recreates Clem's prod situation and verifies aggregates."""
    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            accounts = [
                _bank_dto(
                    "c-bnp", AccountType.CHECKING, "Compte BNP", 2036.77, institution="BNP Paribas"
                ),
                _bank_dto(
                    "c-bp1",
                    AccountType.CHECKING,
                    "Compte BP 1",
                    16.99,
                    institution="Banque Populaire",
                ),
                _bank_dto(
                    "c-bp2",
                    AccountType.CHECKING,
                    "Compte BP 2",
                    0.17,
                    institution="Banque Populaire",
                ),
                _bank_dto(
                    "pea-cash", AccountType.PEA, "PEA Espèces", 3.69, institution="BNP Paribas"
                ),
                _bank_dto(
                    "pea-titres", AccountType.PEA, "PEA Titres", 598.12, institution="BNP Paribas"
                ),
                _bank_dto(
                    "loan-bnp", AccountType.LOAN, "Prêt BNP", -30618.77, institution="BNP Paribas"
                ),
            ]
            account_ids = {}
            for dto in accounts:
                acc_db = await accounts_repo.upsert_account(session, user.id, dto)
                account_ids[dto.provider_account_id] = acc_db.id

            # PEA Titres has 1 holding
            await holdings_repo.replace_holdings(
                session,
                user.id,
                account_ids["pea-titres"],
                [
                    Investment(
                        provider="powens",
                        provider_investment_id="inv-1",
                        provider_account_id="pea-titres",
                        ticker="WPEA.PA",
                        label="iShares MSCI World",
                        quantity=10.0,
                        unit_price=55.0,
                        current_value=598.118,
                        currency="EUR",
                    ),
                ],
            )
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        # Checking total : 2036.77 + 16.99 + 0.17 = 2053.93
        assert abs(wealth.checking_total - 2053.93) < 0.01
        # PEA cash : 3.69
        assert wealth.pea_cash_total == 3.69
        # Investment : 1 PEA Titres with 598.118 valuation
        assert len(wealth.investment_accounts) == 1
        assert abs(wealth.investments_total - 598.118) < 0.01
        # Loan : 30618.77
        assert wealth.total_liabilities == 30618.77
        # Net worth = 2053.93 + 3.69 + 598.118 - 30618.77 ≈ -27963
        assert wealth.net_worth < 0
        assert abs(wealth.net_worth - (-27962.99)) < 0.05
    finally:
        await _cleanup_user(user.id)


@pytest.mark.integration
async def test_wealth_loan_outstanding_uses_used_amount():
    """Loan-like accounts (mortgage…) owe `used_amount`, not |balance|."""
    from app.aggregator import Loan as LoanDTO

    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            dto = _bank_dto(
                "mortgage-1",
                AccountType.MORTGAGE,
                "Prêt immobilier",
                -150000.0,
                raw_data={"loan": {"used_amount": 148250.5, "rate": 1.2}},
            )
            dto.loan = LoanDTO(used_amount=148250.5, total_amount=200000.0, rate=1.2)
            await accounts_repo.upsert_account(session, user.id, dto)
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        assert len(wealth.loans) == 1
        assert wealth.loans[0].outstanding_balance == 148250.5
        assert wealth.total_liabilities == 148250.5
    finally:
        await _cleanup_user(user.id)


@pytest.mark.integration
async def test_wealth_covers_retirement_employee_and_cash_like_types():
    """PER / PEE / AV without positions are valued at their balance; card and
    deposit accounts count as cash. Nothing is silently dropped."""
    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            for dto in [
                _bank_dto("per-1", AccountType.PER, "PER Linxea", 12000.0),
                _bank_dto("pee-1", AccountType.PEE, "PEE Amundi", 3500.0),
                _bank_dto("av-1", AccountType.LIFE_INSURANCE, "AV fonds euros", 20000.0),
                _bank_dto("card-1", AccountType.CARD, "Carte différée", -420.0),
                _bank_dto("dep-1", AccountType.DEPOSIT, "Dépôt", 1000.0),
                _bank_dto("crypto-1", AccountType.CRYPTO, "Coinbase", 800.0),
            ]:
                await accounts_repo.upsert_account(session, user.id, dto)
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        assert {a.account_type for a in wealth.investment_accounts} == {
            "per",
            "pee",
            "life_insurance",
            "crypto",
        }
        assert wealth.investments_total == 12000.0 + 3500.0 + 20000.0 + 800.0
        assert wealth.unrealized_pnl == 0.0  # no positions → no P&L claimed
        assert wealth.checking_total == 1000.0 - 420.0
        assert wealth.net_worth == 36300.0 + 580.0
    finally:
        await _cleanup_user(user.id)


@pytest.mark.integration
async def test_wealth_investment_valuation_preferred_over_balance():
    """When Powens sends a fresher `valuation`, it wins over `balance`."""
    user = await _create_test_user()
    try:
        async with async_session_factory() as session:
            dto = _bank_dto("av-2", AccountType.LIFE_INSURANCE, "AV", 10000.0)
            dto.valuation = 10250.0
            await accounts_repo.upsert_account(session, user.id, dto)
            await session.commit()

            wealth = await get_user_wealth(user=user, session=session)

        assert wealth.investments_total == 10250.0
    finally:
        await _cleanup_user(user.id)
