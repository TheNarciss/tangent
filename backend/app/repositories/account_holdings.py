"""AccountHolding repository — UPSERT + orphan cleanup per bank account.

Holdings are idempotent by design: each sync upserts the current snapshot
and deletes rows that are no longer present.

Race-safety: a transaction-scoped advisory lock keyed on the bank_account_id
serializes concurrent syncs on the *same* account (other accounts still run
in parallel). This was added after observing UniqueViolationError on
uq_holdings_account_provider_inv when two POST /accounts/refresh raced
(React Strict Mode double-mount + auto-refresh useEffect, 2026-05-31).

Cf ADR-002 (multi-tenancy: every read/write filters by user_id).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator import Investment
from ..db.models import AccountHolding

logger = logging.getLogger(__name__)


async def list_holdings(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_account_id: uuid.UUID,
) -> list[AccountHolding]:
    """Holdings of a bank account, filtered by user_id (defense-in-depth)."""
    stmt = (
        select(AccountHolding)
        .where(
            AccountHolding.user_id == user_id,
            AccountHolding.bank_account_id == bank_account_id,
        )
        .order_by(AccountHolding.ticker)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def replace_holdings(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    new_holdings: list[Investment],
) -> list[AccountHolding]:
    """Upsert holdings + delete orphans for one bank account.

    After this call the rows for `bank_account_id` exactly mirror
    `new_holdings`. Safe against concurrent runs on the same account
    (see module docstring).
    """
    # 1. Serialize concurrent syncs on the same bank_account.
    #    pg_advisory_xact_lock(bigint) auto-releases at COMMIT/ROLLBACK.
    #    hashtext() collapses the UUID to int4 → cast to bigint for the lock
    #    key; collisions are statistically negligible and at worst introduce
    #    a brief spurious wait (never data corruption).
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
        {"k": str(bank_account_id)},
    )

    # 2. UPSERT current snapshot — ON CONFLICT updates the mutable fields
    #    (quantity, prices, label may all change between syncs).
    if new_holdings:
        rows = [
            {
                "user_id": user_id,
                "bank_account_id": bank_account_id,
                "provider_investment_id": inv.provider_investment_id,
                "ticker": inv.ticker,
                "isin": inv.isin,
                "label": inv.label,
                "quantity": inv.quantity,
                "unit_price": inv.unit_price,
                "current_value": inv.current_value,
                "currency": inv.currency,
            }
            for inv in new_holdings
        ]
        stmt = pg_insert(AccountHolding).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["bank_account_id", "provider_investment_id"],
            set_={
                "ticker": stmt.excluded.ticker,
                "isin": stmt.excluded.isin,
                "label": stmt.excluded.label,
                "quantity": stmt.excluded.quantity,
                "unit_price": stmt.excluded.unit_price,
                "current_value": stmt.excluded.current_value,
                "currency": stmt.excluded.currency,
            },
        )
        await session.execute(stmt)

    # 3. Remove orphans: rows for this account that vanished from the snapshot.
    #    user_id filter is defense-in-depth (bank_account_id already scoped).
    del_stmt = delete(AccountHolding).where(
        AccountHolding.user_id == user_id,
        AccountHolding.bank_account_id == bank_account_id,
    )
    if new_holdings:
        keep_ids = [inv.provider_investment_id for inv in new_holdings]
        del_stmt = del_stmt.where(AccountHolding.provider_investment_id.notin_(keep_ids))
    del_res = await session.execute(del_stmt)
    removed = del_res.rowcount or 0  # type: ignore[attr-defined]

    await session.commit()

    refreshed = await list_holdings(session, user_id, bank_account_id)
    logger.info(
        "Replaced holdings bank_account=%s: %d rows (%d removed)",
        bank_account_id,
        len(refreshed),
        removed,
    )
    return refreshed


async def update_ter(
    session: AsyncSession,
    user_id: uuid.UUID,
    holding_id: uuid.UUID,
    ter: float,
    source: Literal["api", "llm", "user"] = "user",
) -> AccountHolding | None:
    """Update the TER of a holding, tagging the source. ADR-021.

    Filtered by user_id (multi-tenant: a user can only update their own
    holdings). Returns the updated AccountHolding, or None if the holding
    does not exist or is not owned by the user. Does NOT commit — caller
    must commit.
    """
    now = datetime.now(UTC)
    stmt = (
        update(AccountHolding)
        .where(
            AccountHolding.id == holding_id,
            AccountHolding.user_id == user_id,
        )
        .values(
            ter=ter,
            ter_source=source,
            ter_resolved_at=now,
        )
        .returning(AccountHolding)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_weighted_ter(session: AsyncSession, user_id: uuid.UUID) -> float:
    """Weighted-average TER across the user's holdings (weighted by current_value).

    ADR-021. Holdings with NULL TER count as 0 (don't penalize incomplete data).
    Returns 0.0 if the user has no positive-value holdings.

    SQL-aggregated for efficiency (single round-trip, no Python loop over rows).
    """
    stmt = select(
        func.sum(AccountHolding.current_value * func.coalesce(AccountHolding.ter, 0.0)),
        func.sum(AccountHolding.current_value),
    ).where(
        AccountHolding.user_id == user_id,
        AccountHolding.current_value > 0,
    )
    row = (await session.execute(stmt)).one()
    weighted_sum, total = row[0], row[1]
    if not total or float(total) <= 0:
        return 0.0
    return float(weighted_sum or 0) / float(total)
