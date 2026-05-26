"""Portfolio repository — CRUD pour Portfolio + Positions.

Crée automatiquement un portfolio vide à la première lecture si l'user n'en a
pas encore. Comme ça, après inscription, /portfolio retourne directement un
portfolio vide cohérent.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Portfolio, Position, WatchlistItem

logger = logging.getLogger(__name__)


async def get_or_create(session: AsyncSession, user_id: uuid.UUID) -> Portfolio:
    """Retourne le portfolio de l'user. Crée si absent."""
    stmt = select(Portfolio).where(Portfolio.user_id == user_id)
    result = await session.execute(stmt)
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        portfolio = Portfolio(user_id=user_id, cash=0.0)
        session.add(portfolio)
        await session.commit()
        await session.refresh(portfolio)
        logger.info("Created empty portfolio for user=%s", user_id)
    return portfolio


async def get_positions_with_watchlist(session: AsyncSession, user_id: uuid.UUID) -> list[Position]:
    """Retourne les positions réelles + les watchlist items en tant que positions qty=0.

    Reproduit le comportement de l'ancien portfolio.load() qui mergait
    transactions + watchlist.
    """
    portfolio = await get_or_create(session, user_id)
    positions = list(portfolio.positions)

    held_tickers = {p.ticker for p in positions}

    stmt = select(WatchlistItem).where(WatchlistItem.user_id == user_id)
    result = await session.execute(stmt)
    watchlist_items = result.scalars().all()

    for w in watchlist_items:
        if w.ticker not in held_tickers:
            # Position éphémère (pas persistée) — juste pour exposer le ticker dans le dashboard
            positions.append(
                Position(
                    portfolio_id=portfolio.id,
                    ticker=w.ticker,
                    quantity=0.0,
                    avg_cost=0.0,
                )
            )
    return positions


async def replace_positions(
    session: AsyncSession,
    user_id: uuid.UUID,
    new_positions: list[dict],
    cash: float | None = None,
) -> Portfolio:
    """Remplace toutes les positions du user.

    new_positions est une liste de dicts : {ticker, quantity, avg_cost, isin?, label?}.
    Utilisé par PUT /portfolio (édition manuelle) et plus tard /sync/powens.
    """
    portfolio = await get_or_create(session, user_id)

    # Vide les positions existantes (relation cascade)
    for old in list(portfolio.positions):
        await session.delete(old)
    await session.flush()
    # Ajoute les nouvelles
    for p in new_positions:
        if p.get("quantity", 0) <= 0:
            continue  # skip qty=0 — les watchlist sont une table séparée
        portfolio.positions.append(
            Position(
                portfolio_id=portfolio.id,
                ticker=p["ticker"],
                quantity=float(p["quantity"]),
                avg_cost=float(p.get("avg_cost", 0)),
                isin=p.get("isin"),
                label=p.get("label"),
            )
        )

    if cash is not None:
        portfolio.cash = float(cash)

    await session.commit()
    await session.refresh(portfolio)
    return portfolio
