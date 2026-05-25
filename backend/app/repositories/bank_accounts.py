"""BankAccount repository — CRUD multi-tenant (ADR-002, ADR-008).

Every method filters by user_id to guarantee multi-tenant isolation.
Tied to provider data via (provider, provider_account_id) for idempotent
upserts from the aggregator layer.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator import BankAccount as BankAccountDTO
from ..db.models import BankAccount

logger = logging.getLogger(__name__)


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

    Used by the aggregator sync flow: each provider account corresponds to
    exactly one row per user.
    """
    stmt = select(BankAccount).where(
        BankAccount.user_id == user_id,
        BankAccount.provider == account_dto.provider,
        BankAccount.provider_account_id == account_dto.provider_account_id,
    )
    res = await session.execute(stmt)
    row = res.scalars().first()

    if row is None:
        row = BankAccount(
            user_id=user_id,
            provider=account_dto.provider,
            provider_account_id=account_dto.provider_account_id,
            name=account_dto.name,
            type=account_dto.type.value,
            currency=account_dto.currency,
            balance=account_dto.balance,
            iban=account_dto.iban,
            institution_name=account_dto.institution_name,
            last_synced_at=account_dto.last_synced_at,
        )
        session.add(row)
        logger.info(
            "Created bank_account user=%s provider=%s acc=%s",
            user_id,
            account_dto.provider,
            account_dto.provider_account_id,
        )
    else:
        row.name = account_dto.name
        row.type = account_dto.type.value
        row.currency = account_dto.currency
        row.balance = account_dto.balance
        row.iban = account_dto.iban
        row.institution_name = account_dto.institution_name
        row.last_synced_at = account_dto.last_synced_at

    await session.commit()
    await session.refresh(row)
    return row


async def delete_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> bool:
    """Delete a bank account + cascade holdings/transactions. Returns True if deleted."""
    row = await get_account(session, user_id, account_id)
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    logger.info("Deleted bank_account=%s for user=%s", account_id, user_id)
    return True
