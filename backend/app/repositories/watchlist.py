"""Watchlist repository — CRUD pour les tickers suivis sans transaction."""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import WatchlistItem

logger = logging.getLogger(__name__)


async def list_tickers(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """Liste des tickers suivis (juste les strings, pour exposer côté API)."""
    stmt = select(WatchlistItem.ticker).where(WatchlistItem.user_id == user_id)
    result = await session.execute(stmt)
    return [r[0] for r in result.all()]


async def add(session: AsyncSession, user_id: uuid.UUID, ticker: str) -> list[str]:
    """Ajoute un ticker. Idempotent (unique constraint = no double)."""
    t = ticker.strip().upper()
    if not t:
        return await list_tickers(session, user_id)
    item = WatchlistItem(user_id=user_id, ticker=t)
    session.add(item)
    try:
        await session.commit()
        logger.info("Watchlist: added %s for user=%s", t, user_id)
    except IntegrityError:
        # Déjà présent — pas d'erreur côté API, on retourne juste la liste actuelle
        await session.rollback()
    return await list_tickers(session, user_id)


async def remove(session: AsyncSession, user_id: uuid.UUID, ticker: str) -> list[str]:
    """Retire un ticker. No-op si pas présent."""
    t = ticker.strip().upper()
    stmt = select(WatchlistItem).where(
        WatchlistItem.user_id == user_id, WatchlistItem.ticker == t,
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item:
        await session.delete(item)
        await session.commit()
        logger.info("Watchlist: removed %s for user=%s", t, user_id)
    return await list_tickers(session, user_id)