"""Alembic env.py — async, branché sur app.* metadata.

Run: `alembic revision --autogenerate -m "msg"` or `alembic upgrade head`.
DATABASE_URL doit être set dans l'env (sinon fallback dev local).
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add backend/ to sys.path so we can import `app.*`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Charge .env si présent (pratique en dev local)
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# ─── Target metadata ──────────────────────────────────────────────────────
# Importer Base depuis auth.models (où il est défini)
# PUIS importer db.models pour que les tables s'enregistrent dans la metadata
# (sinon autogenerate ne voit que la table users)
from app.auth.models import Base  # noqa: E402
import app.db.models  # noqa: E402, F401 — side effect: registers tables

target_metadata = Base.metadata

# ─── Alembic Config ───────────────────────────────────────────────────────
config = context.config

# Inject DATABASE_URL from env (overrides ini)
db_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://tangent:tangent_dev@localhost:5432/tangent",
)
config.set_main_option("sqlalchemy.url", db_url)

# Logging config (fileConfig from alembic.ini)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ─── Offline mode ─────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Génère le SQL sans connexion DB (utile pour audit)."""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


# ─── Online mode (async) ──────────────────────────────────────────────────
def render_item(type_, obj, autogen_context):
    """Auto-import des types custom (fastapi-users GUID) dans les migrations."""
    if type_ == "type" and obj.__class__.__module__.startswith("fastapi_users_db_sqlalchemy"):
        autogen_context.imports.add("import fastapi_users_db_sqlalchemy")
        return "fastapi_users_db_sqlalchemy.generics.GUID()"
    return False  # default rendering


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
