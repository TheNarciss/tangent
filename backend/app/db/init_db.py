"""Schema migrations au startup — via Alembic subprocess.

Phase 0 → Alembic :
- Dev fresh install : `alembic upgrade head` crée les 8 tables.
- Dev existant : DB déjà stampée → `upgrade head` est no-op.
- Prod : pareil après `alembic stamp head` sur la DB existante (1 fois).
- Tests : conftest fait `Base.metadata.create_all` manuellement
  (ASGITransport ne déclenche pas le lifespan).

IMPORTANT: We invoke alembic as a subprocess instead of calling
`command.upgrade()` directly. The latter creates a nested `asyncio.run()`
inside FastAPI's parent event loop, which deadlocks at startup because
the inner loop's shutdown waits indefinitely on asyncpg cleanup that's
holding resources from the parent loop. Subprocess isolation eliminates
the nesting and the deadlock.

Refs: FastAPI #13008, Alembic #1606.
"""

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import text

from .engine import engine

logger = logging.getLogger(__name__)

# backend/ is two levels up from app/db/init_db.py
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"


async def init_db() -> None:
    """Apply DB migrations to head via an alembic subprocess.

    Idempotent: si la DB est déjà à head, c'est un no-op (rien créé).
    Raises RuntimeError if the migration command exits non-zero.
    """
    if not _ALEMBIC_INI.exists():
        logger.error("alembic.ini not found at %s, skipping migrations", _ALEMBIC_INI)
        return

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(_ALEMBIC_INI),
        "upgrade",
        "head",
        cwd=str(_BACKEND_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout_bytes, _ = await proc.communicate()
    output = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""

    if proc.returncode != 0:
        logger.error(
            "Alembic migration failed (exit=%s):\n%s",
            proc.returncode,
            output,
        )
        raise RuntimeError(f"Alembic upgrade failed with exit code {proc.returncode}")

    if output.strip():
        logger.info("Alembic output:\n%s", output.rstrip())
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
