"""Transactions repository — historique des opérations PEA.

Pour l'instant les transactions sont déconnectées du calcul de positions
(qui passe par Portfolio + Positions). Elles servent à l'audit + reporting.

Plus tard (Phase ultérieure) on pourra reconstruire les positions depuis
les transactions à la demande, mais pour l'instant on garde les 2 séparés
pour simplicité.
"""

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Transaction, TransactionKind

logger = logging.getLogger(__name__)


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 200,
) -> list[Transaction]:
    """Liste les transactions d'un user, les plus récentes d'abord."""
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.occurred_on.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def add(
    session: AsyncSession,
    user_id: uuid.UUID,
    occurred_on: date,
    kind: TransactionKind,
    ticker: str | None = None,
    quantity: float = 0.0,
    price: float = 0.0,
    fees: float = 0.0,
    note: str | None = None,
) -> Transaction:
    """Ajoute une transaction."""
    tx = Transaction(
        user_id=user_id,
        occurred_on=occurred_on,
        kind=kind,
        ticker=ticker.strip().upper() if ticker else None,
        quantity=quantity,
        price=price,
        fees=fees,
        note=note,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    logger.info(
        "Transaction added for user=%s: %s %s %s qty=%.2f price=%.2f",
        user_id,
        kind,
        ticker,
        occurred_on,
        quantity,
        price,
    )
    return tx


async def delete(session: AsyncSession, user_id: uuid.UUID, tx_id: uuid.UUID) -> bool:
    """Supprime une transaction. Retourne False si pas trouvée OU pas owned par user."""
    stmt = select(Transaction).where(
        Transaction.id == tx_id,
        Transaction.user_id == user_id,
    )
    result = await session.execute(stmt)
    tx = result.scalar_one_or_none()
    if tx is None:
        return False
    await session.delete(tx)
    await session.commit()
    return True
