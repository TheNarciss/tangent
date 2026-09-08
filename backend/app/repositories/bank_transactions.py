"""BankTransaction repository — append-only with idempotent upsert.

Bank transactions are immutable once posted: we never UPDATE them, we INSERT
new ones with ON CONFLICT DO NOTHING. This preserves the full history even
across multiple syncs.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator import Transaction
from ..db.models import BankAccount, BankTransaction

logger = logging.getLogger(__name__)


async def list_transactions(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
) -> list[BankTransaction]:
    """Most recent transactions first, optionally filtered by date range."""
    stmt = (
        select(BankTransaction)
        .where(
            BankTransaction.user_id == user_id,
            BankTransaction.bank_account_id == bank_account_id,
        )
        .order_by(BankTransaction.transaction_date.desc())
        .limit(limit)
    )
    if start_date is not None:
        stmt = stmt.where(BankTransaction.transaction_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(BankTransaction.transaction_date <= end_date)

    res = await session.execute(stmt)
    return list(res.scalars().all())


async def upsert_transactions(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    new_txs: list[Transaction],
) -> int:
    """INSERT ON CONFLICT DO NOTHING on (bank_account_id, provider_transaction_id).

    Returns the number of newly inserted rows. Existing rows are left untouched.
    Append-only by design: bank transactions are immutable once they occur.
    """
    if not new_txs:
        return 0

    rows = [
        {
            "user_id": user_id,
            "bank_account_id": bank_account_id,
            "provider_transaction_id": tx.provider_transaction_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "transaction_date": tx.transaction_date,
            "description": tx.description,
            "category": tx.category,
        }
        for tx in new_txs
    ]

    stmt = pg_insert(BankTransaction).values(rows)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["bank_account_id", "provider_transaction_id"]
    )
    res = await session.execute(stmt)
    await session.commit()

    # SQLAlchemy's typed Result[Any] hides .rowcount, but execute() on a DML
    # statement actually returns CursorResult which exposes it. Justified ignore.
    inserted = res.rowcount or 0  # type: ignore[attr-defined]
    logger.info(
        "Inserted %d new bank_tx for bank_account=%s (skipped %d duplicates)",
        inserted,
        bank_account_id,
        len(rows) - inserted,
    )
    return inserted


async def update_category(
    session: AsyncSession,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    category: str,
    source: Literal["api", "llm", "user"] = "user",
) -> BankTransaction | None:
    """Update the category of a bank transaction, tagging the source. ADR-021.

    Filtered by user_id (multi-tenant). Returns the updated row or None if
    not found / not owned. Does NOT commit — caller must commit.
    """
    now = datetime.now(UTC)
    stmt = (
        update(BankTransaction)
        .where(
            BankTransaction.id == transaction_id,
            BankTransaction.user_id == user_id,
        )
        .values(
            category=category,
            category_source=source,
            category_resolved_at=now,
        )
        .returning(BankTransaction)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_recent_all_accounts(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
) -> list[tuple[BankTransaction, BankAccount]]:
    """Latest N transactions across ALL bank accounts of the user.

    Joined with BankAccount so the response can include the account name
    (used by the Dashboard 'Mouvements récents' tile for context).
    Ordered by transaction_date desc, with id as tiebreaker for stability.
    """
    stmt = (
        select(BankTransaction, BankAccount)
        .join(BankAccount, BankTransaction.bank_account_id == BankAccount.id)
        .where(BankTransaction.user_id == user_id)
        .order_by(
            BankTransaction.transaction_date.desc(),
            BankTransaction.id.desc(),
        )
        .limit(limit)
    )
    res = await session.execute(stmt)
    return [(tx, acc) for tx, acc in res.all()]


# Accounts whose debits are day-to-day spending (transfers out of savings or
# investment wrappers are not expenses).
_SPENDING_ACCOUNT_TYPES = ("checking", "card", "joint")


async def monthly_outflow(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    days: int = 90,
) -> float | None:
    """Average monthly debits on the user's current accounts over `days` days.

    Feeds the précaution step of the « prochain euro » verdict. Transfers to
    a livret or a PEA count as debits here, which overstates spending a
    little and therefore the précaution target: prudent by construction.
    Returns None when no debit was synced in the window.
    """
    since = date.today() - timedelta(days=days)
    stmt = (
        select(func.sum(BankTransaction.amount))
        .join(BankAccount, BankTransaction.bank_account_id == BankAccount.id)
        .where(
            BankTransaction.user_id == user_id,
            BankTransaction.transaction_date >= since,
            BankTransaction.amount < 0,
            BankAccount.type.in_(_SPENDING_ACCOUNT_TYPES),
        )
    )
    total = (await session.execute(stmt)).scalar()
    if total is None:
        return None
    return -float(total) / (days / 30.4375)


# Accounts a transfer *into* is saving: regulated envelopes and investment wrappers.
_SAVING_ACCOUNT_TYPES = (
    "livret_a",
    "livret_b",
    "ldds",
    "lep",
    "pel",
    "cel",
    "csl",
    "cat",
    "pea",
    "cto",
    "life_insurance",
    "per",
    "capitalisation",
)


async def monthly_inflow_to_savings(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    days: int = 90,
) -> float | None:
    """Average monthly credits on savings and investment accounts over `days` days.

    Feeds the « taux d'épargne » verdict as the observed saving, next to the
    monthly contribution the profile declares. Interest credited by the bank
    counts too, which overstates it slightly. None when nothing was synced.
    """
    since = date.today() - timedelta(days=days)
    stmt = (
        select(func.sum(BankTransaction.amount))
        .join(BankAccount, BankTransaction.bank_account_id == BankAccount.id)
        .where(
            BankTransaction.user_id == user_id,
            BankTransaction.transaction_date >= since,
            BankTransaction.amount > 0,
            BankAccount.type.in_(_SAVING_ACCOUNT_TYPES),
        )
    )
    total = (await session.execute(stmt)).scalar()
    if total is None:
        return None
    return float(total) / (days / 30.4375)
