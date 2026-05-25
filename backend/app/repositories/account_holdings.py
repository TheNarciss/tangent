"""AccountHolding repository — replace-all pattern per bank account.

Holdings are idempotent by design: each sync wipes existing rows and re-inserts
the current snapshot. This avoids the complexity of diff-merge logic for what
is effectively a point-in-time photograph of the portfolio.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select
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
    """Wipe + insert all holdings of a bank account.

    Idempotent: running with the same Investment list twice yields the same
    DB state. Used after every Powens sync.
    """
    # Bulk delete in 1 statement (perf) + flush so INSERT below doesn't hit
    # the unique constraint on (bank_account_id, provider_investment_id)
    delete_stmt = delete(AccountHolding).where(
        AccountHolding.user_id == user_id,
        AccountHolding.bank_account_id == bank_account_id,
    )
    delete_result = await session.execute(delete_stmt)
    await session.flush()
    removed = delete_result.rowcount or 0  # type: ignore[attr-defined]

    persisted: list[AccountHolding] = []
    for inv in new_holdings:
        row = AccountHolding(
            user_id=user_id,
            bank_account_id=bank_account_id,
            provider_investment_id=inv.provider_investment_id,
            ticker=inv.ticker,
            isin=inv.isin,
            label=inv.label,
            quantity=inv.quantity,
            unit_price=inv.unit_price,
            current_value=inv.current_value,
            currency=inv.currency,
        )
        session.add(row)
        persisted.append(row)

    await session.commit()
    for row in persisted:
        await session.refresh(row)

    logger.info(
        "Replaced holdings bank_account=%s: %d new rows (%d removed)",
        bank_account_id,
        len(persisted),
        removed,
    )
    return persisted
