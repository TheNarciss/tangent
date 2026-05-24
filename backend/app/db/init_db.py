"""Schema migrations au startup — via Alembic.

Phase 0 → Alembic :
- Dev fresh install : `alembic upgrade head` crée les 8 tables.
- Dev existant : DB déjà stampée → `upgrade head` est no-op.
- Prod : pareil après `alembic stamp head` sur la DB existante (1 fois).
- Tests : conftest fait `Base.metadata.create_all` manuellement
  (ASGITransport ne déclenche pas le lifespan).
"""

import asyncio
import logging
from pathlib import Path

from alembic.config import Config
from sqlalchemy import text

from alembic import command

from .engine import engine

logger = logging.getLogger(__name__)

# alembic.ini est dans backend/ (2 niveaux au-dessus de app/db/init_db.py)
_ALEMBIC_INI = Path(__file__).resolve().parent.parent.parent / "alembic.ini"


def _run_migrations_sync() -> None:
    """Run alembic upgrade head — sync, à wrapper dans to_thread."""
    cfg = Config(str(_ALEMBIC_INI))
    command.upgrade(cfg, "head")


async def init_db() -> None:
    """Apply DB migrations to head. Called by lifespan at startup.

    Idempotent: si la DB est déjà à head, c'est un no-op (rien créé).
    """
    if not _ALEMBIC_INI.exists():
        logger.error("alembic.ini not found at %s, skipping migrations", _ALEMBIC_INI)
        return
    await asyncio.to_thread(_run_migrations_sync)
    logger.info("DB migrations applied (alembic upgrade head)")


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
