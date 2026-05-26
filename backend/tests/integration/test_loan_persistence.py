"""Integration tests for the BankAccount extended schema + Loan upsert (ADR-013).

Validates:
- All Powens hot fields are persisted on BankAccount
- Nested Loan DTO triggers Loan row upsert (one-to-one)
- raw_data JSONB stores the full Powens payload (no data loss)
- Idempotent re-sync updates fields without duplicating rows
- Loan-less account doesn't create a Loan row
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from app.aggregator import AccountType
from app.aggregator import BankAccount as BankAccountDTO
from app.aggregator import Loan as LoanDTO
from app.auth.models import User
from app.db.engine import async_session_factory
from app.repositories import bank_accounts as accounts_repo
from app.repositories import loans as loans_repo

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Test fixtures helpers ──────────────────────────────────────────────────


async def _create_user(session, email: str = "loan-test@x.com") -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="x" * 60,
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _make_loan_account_dto(provider_id: str = "999") -> BankAccountDTO:
    """A BankAccount DTO with a nested Loan, mimicking Powens payload."""
    loan_raw = {
        "id": 8,
        "id_account": int(provider_id),
        "total_amount": 30000.0,
        "available_amount": None,
        "used_amount": None,
        "subscription_date": None,
        "maturity_date": "2036-12-04 00:00:00",
        "start_repayment_date": None,
        "deferred": True,
        "next_payment_amount": 0.0,
        "next_payment_date": "2036-12-04 00:00:00",
        "last_payment_amount": None,
        "last_payment_date": None,
        "nb_payments_done": None,
        "nb_payments_left": 127,
        "nb_payments_total": None,
        "rate": 2.0,
        "duration": 144,
        "insurance_label": None,
        "insurance_amount": 0.0,
        "insurance_rate": None,
        "account_label": None,
        "type": "consumercredit",
    }
    acc_raw = {
        "id": int(provider_id),
        "id_user": 18,
        "id_connection": 13,
        "name": "Prêt personnel",
        "type": "loan",
        "balance": -30618.77,
        "currency": {"id": "EUR", "symbol": "€"},
        "loan": loan_raw,
        "bic": None,
        "iban": None,
        "number": "****7727",
        "webid": "abc123",  # un champ non-hot, doit aller dans raw_data
    }
    return BankAccountDTO(
        provider="powens",
        provider_account_id=provider_id,
        name="Prêt personnel",
        type=AccountType.LOAN,
        currency="EUR",
        institution_name="BNP Paribas",
        balance=-30618.77,
        number="****7727",
        bookmarked=False,
        display=False,
        loan=LoanDTO(
            total_amount=30000.0,
            maturity_date=date(2036, 12, 4),
            deferred=True,
            next_payment_amount=0.0,
            next_payment_date=date(2036, 12, 4),
            nb_payments_left=127,
            rate=2.0,
            duration_months=144,
            insurance_amount=0.0,
            loan_type="consumercredit",
            raw_data=loan_raw,
        ),
        raw_data=acc_raw,
        last_synced_at=datetime.now(UTC),
    )


def _make_checking_account_dto(provider_id: str = "1001") -> BankAccountDTO:
    """A simple checking account DTO (no Loan)."""
    return BankAccountDTO(
        provider="powens",
        provider_account_id=provider_id,
        name="Compte courant",
        type=AccountType.CHECKING,
        currency="EUR",
        institution_name="BNP Paribas",
        balance=2036.77,
        iban="FR7630004000310000118544841",
        bic="BNPAFRPPXXX",
        usage="PRIV",
        ownership="owner",
        last_synced_at=datetime.now(UTC),
        raw_data={"id": int(provider_id), "type": "checking", "balance": 2036.77},
    )


# ── Tests ──────────────────────────────────────────────────────────────────


async def test_upsert_loan_account_persists_all_hot_fields(client):
    async with async_session_factory() as session:
        user = await _create_user(session, email=f"t1-{uuid.uuid4().hex[:8]}@x.com")
        dto = _make_loan_account_dto()

        row = await accounts_repo.upsert_account(session, user.id, dto)

        assert row.type == "loan"
        assert row.name == "Prêt personnel"
        assert row.balance == -30618.77
        assert row.institution_name == "BNP Paribas"
        assert row.number == "****7727"
        assert row.display is False
        assert row.bookmarked is False
        # raw_data should contain the original Powens payload
        assert row.raw_data["webid"] == "abc123"  # not promoted to column
        assert row.raw_data["id_connection"] == 13


async def test_upsert_loan_account_creates_loan_row(client):
    async with async_session_factory() as session:
        user = await _create_user(session, email=f"t2-{uuid.uuid4().hex[:8]}@x.com")
        dto = _make_loan_account_dto()

        account_row = await accounts_repo.upsert_account(session, user.id, dto)

        loan = await loans_repo.get_loan_by_account(session, user.id, account_row.id)
        assert loan is not None
        assert loan.total_amount == 30000.0
        assert loan.rate == 2.0
        assert loan.deferred is True
        assert loan.nb_payments_left == 127
        assert loan.duration_months == 144
        assert loan.maturity_date == date(2036, 12, 4)
        assert loan.loan_type == "consumercredit"
        assert loan.raw_data["id"] == 8


async def test_upsert_checking_account_does_not_create_loan(client):
    async with async_session_factory() as session:
        user = await _create_user(session, email=f"t3-{uuid.uuid4().hex[:8]}@x.com")
        dto = _make_checking_account_dto()

        account_row = await accounts_repo.upsert_account(session, user.id, dto)

        loan = await loans_repo.get_loan_by_account(session, user.id, account_row.id)
        assert loan is None  # no nested Loan DTO → no Loan row


async def test_upsert_loan_account_idempotent_updates_in_place(client):
    async with async_session_factory() as session:
        user = await _create_user(session, email=f"t4-{uuid.uuid4().hex[:8]}@x.com")
        dto = _make_loan_account_dto()

        row1 = await accounts_repo.upsert_account(session, user.id, dto)
        loan1 = await loans_repo.get_loan_by_account(session, user.id, row1.id)
        assert loan1.rate == 2.0

        # Renegotiation: rate changed
        dto.loan.rate = 1.8
        dto.balance = -30500.0
        row2 = await accounts_repo.upsert_account(session, user.id, dto)

        assert row2.id == row1.id
        assert row2.balance == -30500.0

        loan2 = await loans_repo.get_loan_by_account(session, user.id, row2.id)
        assert loan2.id == loan1.id  # same Loan row, updated
        assert loan2.rate == 1.8


async def test_total_monthly_payments_aggregates(client):
    async with async_session_factory() as session:
        user = await _create_user(session, email=f"t5-{uuid.uuid4().hex[:8]}@x.com")

        dto1 = _make_loan_account_dto(provider_id="201")
        dto1.loan.next_payment_amount = 250.0
        await accounts_repo.upsert_account(session, user.id, dto1)

        dto2 = _make_loan_account_dto(provider_id="202")
        dto2.loan.next_payment_amount = 1300.0
        await accounts_repo.upsert_account(session, user.id, dto2)

        total = await loans_repo.total_monthly_payments(session, user.id)
        assert total == 1550.0


async def test_list_accounts_returns_extended_account(client):
    async with async_session_factory() as session:
        user = await _create_user(session, email=f"t6-{uuid.uuid4().hex[:8]}@x.com")
        await accounts_repo.upsert_account(session, user.id, _make_checking_account_dto())
        await accounts_repo.upsert_account(session, user.id, _make_loan_account_dto())

        rows = await accounts_repo.list_accounts(session, user.id)
        assert len(rows) == 2
        by_type = {r.type: r for r in rows}
        assert "checking" in by_type
        assert "loan" in by_type
        assert by_type["checking"].iban == "FR7630004000310000118544841"
        assert by_type["loan"].balance == -30618.77


async def test_multi_tenant_isolation_loans(client):
    async with async_session_factory() as session:
        user_a = await _create_user(session, email=f"alice-{uuid.uuid4().hex[:8]}@x.com")
        user_b = await _create_user(session, email=f"bob-{uuid.uuid4().hex[:8]}@x.com")

        await accounts_repo.upsert_account(
            session, user_a.id, _make_loan_account_dto(provider_id="300")
        )
        await accounts_repo.upsert_account(
            session, user_b.id, _make_loan_account_dto(provider_id="301")
        )

        a_loans = await loans_repo.list_loans(session, user_a.id)
        b_loans = await loans_repo.list_loans(session, user_b.id)
        assert len(a_loans) == 1
        assert len(b_loans) == 1
        assert a_loans[0].id != b_loans[0].id
