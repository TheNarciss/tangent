"""Loan repository — read-side queries (ADR-002, ADR-013).

Write-side (upsert) is handled inside bank_accounts.upsert_account when a
DTO carries a nested Loan, to keep BankAccount + Loan transactionally
consistent.

This module provides read helpers for endpoints / dashboards that need to
query loans directly (e.g. project remaining capital, sum monthly payments).
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Loan

logger = logging.getLogger(__name__)


async def list_loans(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[Loan]:
    """All loans owned by a user, ordered by next payment date (soonest first)."""
    stmt = (
        select(Loan)
        .where(Loan.user_id == user_id)
        .order_by(Loan.next_payment_date.asc().nullslast())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def get_loan_by_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_account_id: uuid.UUID,
) -> Loan | None:
    """Single loan attached to a specific BankAccount (user-scoped)."""
    stmt = select(Loan).where(
        Loan.user_id == user_id,
        Loan.bank_account_id == bank_account_id,
    )
    res = await session.execute(stmt)
    return res.scalars().first()


async def total_monthly_payments(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> float:
    """Sum of next_payment_amount across all loans for a user.

    Returns 0.0 if no loans or all loans have null next_payment_amount.
    Useful for dashboard "monthly debt service" line.
    """
    stmt = select(Loan.next_payment_amount).where(
        Loan.user_id == user_id,
        Loan.next_payment_amount.is_not(None),
    )
    res = await session.execute(stmt)
    values = [v for v in res.scalars().all() if v is not None]
    return float(sum(values))


async def total_capital_owed(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> float:
    """Sum of used_amount across all loans (= total capital still owed).

    Reads from Loan.used_amount which Powens populates as capital actually
    drawn. Returns 0.0 if no loans.
    """
    stmt = select(Loan.used_amount).where(
        Loan.user_id == user_id,
        Loan.used_amount.is_not(None),
    )
    res = await session.execute(stmt)
    values = [v for v in res.scalars().all() if v is not None]
    return float(sum(values))
