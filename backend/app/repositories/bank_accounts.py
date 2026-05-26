"""BankAccount + Loan repository — multi-tenant CRUD (ADR-002, ADR-008, ADR-013).

Every method filters by user_id (multi-tenant isolation).
Persistence pattern: hot fields → typed columns, full payload → raw_data JSONB.

When the DTO has a nested `loan` (loan-like accounts), it is upserted in the
same call to keep BankAccount + Loan transactionally consistent.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator import BankAccount as BankAccountDTO
from ..db.models import BankAccount, Loan

logger = logging.getLogger(__name__)


# ── BankAccount field set extracted from DTO ───────────────────────────────


def _dto_to_account_kwargs(dto: BankAccountDTO) -> dict:
    """Convert a BankAccount DTO into the kwargs dict for ORM column assignment."""
    return {
        # Identification
        "name": dto.name,
        "type": dto.type.value,
        "currency": dto.currency,
        "institution_name": dto.institution_name,
        # Identifiers
        "iban": dto.iban,
        "bic": dto.bic,
        "number": dto.number,
        # Balance & valuation
        "balance": dto.balance,
        "valuation": dto.valuation,
        "coming": dto.coming,
        "coming_balance": dto.coming_balance,
        "diff": dto.diff,
        "diff_percent": dto.diff_percent,
        "prev_diff": dto.prev_diff,
        "prev_diff_percent": dto.prev_diff_percent,
        # Context
        "usage": dto.usage,
        "ownership": dto.ownership,
        "company_name": dto.company_name,
        "opening_date": dto.opening_date,
        # State
        "bookmarked": dto.bookmarked,
        "display": dto.display,
        "powens_deleted_at": dto.powens_deleted_at,
        "powens_disabled_at": dto.powens_disabled_at,
        "powens_error": dto.powens_error,
        "powens_last_update": dto.powens_last_update,
        # Sync
        "last_synced_at": dto.last_synced_at,
        # JSONB raw payload
        "raw_data": dto.raw_data or {},
    }


# ── Public API ─────────────────────────────────────────────────────────────


async def list_accounts(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[BankAccount]:
    """All bank accounts of a user, sorted by name."""
    stmt = select(BankAccount).where(BankAccount.user_id == user_id).order_by(BankAccount.name)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def get_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> BankAccount | None:
    """Single bank account, filtered by user_id (multi-tenant safety)."""
    stmt = select(BankAccount).where(
        BankAccount.id == account_id,
        BankAccount.user_id == user_id,
    )
    res = await session.execute(stmt)
    return res.scalars().first()


async def upsert_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_dto: BankAccountDTO,
) -> BankAccount:
    """Insert or update based on (user_id, provider, provider_account_id).

    If the DTO carries a `loan` sub-object, also upserts the Loan row
    transactionally (one-to-one with the BankAccount).
    """
    stmt = select(BankAccount).where(
        BankAccount.user_id == user_id,
        BankAccount.provider == account_dto.provider,
        BankAccount.provider_account_id == account_dto.provider_account_id,
    )
    res = await session.execute(stmt)
    row = res.scalars().first()

    kwargs = _dto_to_account_kwargs(account_dto)

    if row is None:
        row = BankAccount(
            user_id=user_id,
            provider=account_dto.provider,
            provider_account_id=account_dto.provider_account_id,
            **kwargs,
        )
        session.add(row)
        await session.flush()  # so row.id is populated for the Loan FK
        logger.info(
            "Created bank_account user=%s provider=%s acc=%s",
            user_id,
            account_dto.provider,
            account_dto.provider_account_id,
        )
    else:
        for k, v in kwargs.items():
            setattr(row, k, v)

    # ── Nested Loan upsert (one-to-one) ────────────────────────────────────
    if account_dto.loan is not None:
        await _upsert_loan(session, user_id, row.id, account_dto.loan)

    await session.commit()
    await session.refresh(row)
    return row


async def _upsert_loan(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    loan_dto,
) -> Loan:
    """Insert/update the Loan row attached to a BankAccount. Internal helper."""
    stmt = select(Loan).where(Loan.bank_account_id == bank_account_id)
    res = await session.execute(stmt)
    row = res.scalars().first()

    kwargs = {
        "total_amount": loan_dto.total_amount,
        "available_amount": loan_dto.available_amount,
        "used_amount": loan_dto.used_amount,
        "subscription_date": loan_dto.subscription_date,
        "maturity_date": loan_dto.maturity_date,
        "start_repayment_date": loan_dto.start_repayment_date,
        "deferred": loan_dto.deferred,
        "next_payment_amount": loan_dto.next_payment_amount,
        "next_payment_date": loan_dto.next_payment_date,
        "last_payment_amount": loan_dto.last_payment_amount,
        "last_payment_date": loan_dto.last_payment_date,
        "nb_payments_done": loan_dto.nb_payments_done,
        "nb_payments_left": loan_dto.nb_payments_left,
        "nb_payments_total": loan_dto.nb_payments_total,
        "rate": loan_dto.rate,
        "duration_months": loan_dto.duration_months,
        "insurance_label": loan_dto.insurance_label,
        "insurance_amount": loan_dto.insurance_amount,
        "insurance_rate": loan_dto.insurance_rate,
        "account_label": loan_dto.account_label,
        "loan_type": loan_dto.loan_type,
        "raw_data": loan_dto.raw_data or {},
    }

    if row is None:
        row = Loan(
            user_id=user_id,
            bank_account_id=bank_account_id,
            **kwargs,
        )
        session.add(row)
        logger.info("Created loan for bank_account=%s", bank_account_id)
    else:
        for k, v in kwargs.items():
            setattr(row, k, v)

    return row


async def delete_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> bool:
    """Delete a bank account + cascade Loan/holdings/transactions."""
    row = await get_account(session, user_id, account_id)
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    logger.info("Deleted bank_account=%s for user=%s", account_id, user_id)
    return True
