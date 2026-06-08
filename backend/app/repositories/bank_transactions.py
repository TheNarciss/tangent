"""BankTransaction repository — append-only with idempotent upsert.

Bank transactions are immutable once posted: we never UPDATE them, we INSERT
new ones with ON CONFLICT DO NOTHING. This preserves the full history even
across multiple syncs.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator import Transaction
from ..db.models import BankTransaction

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
