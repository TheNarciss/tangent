"""Création initiale du schéma DB.

En dev on utilise create_all pour démarrer vite. En prod : Alembic migrations
(à faire en Phase 6 si besoin).

create_all est idempotent — si la table existe déjà, elle n'est pas recréée
ni modifiée. Pour modifier le schéma il faudra passer à Alembic.
"""

import logging

from sqlalchemy import text

from ..auth.models import Base
from .engine import engine

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Crée les tables si elles n'existent pas. À appeler au startup FastAPI.

    create_all utilise les metadata de Base (qui inclut User et toutes
    les futures tables qui hériteront de Base — Position, Portfolio, etc.).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB schema initialized (create_all)")


async def db_ready() -> bool:
    """True si la DB répond ET que la table users existe."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM information_schema.tables WHERE table_name = 'users'")
            )
            return result.first() is not None
    except Exception as exc:
        logger.warning("DB readiness check failed: %s", exc)
        return False
