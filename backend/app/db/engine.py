"""Async SQLAlchemy engine + session factory pour PostgreSQL.

Phase 1 : juste un ping de santé. Les modèles arrivent en Phase 2 avec FastAPI-Users.

DATABASE_URL est passée par env (docker-compose la fournit automatiquement).
Format attendu : postgresql+asyncpg://user:password@host:port/dbname
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

# Fallback local pour les devs qui lancent uvicorn hors Docker
_DEFAULT_URL = "postgresql+asyncpg://tangent:tangent_dev@localhost:5432/tangent"
DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_URL)


# Engine singleton — partagé entre tous les requests (pool de connexions)
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,           # passe à True pour voir toutes les queries en debug
    pool_pre_ping=True,   # vérifie la connexion avant de la réutiliser (évite "stale connection")
    pool_size=5,          # 5 connexions simultanées — largement assez pour 7 users
    max_overflow=10,
)

# Session factory — async, à utiliser via FastAPI Depends()
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency : injecte une AsyncSession dans les endpoints."""
    async with async_session_factory() as session:
        yield session


async def ping() -> bool:
    """True si la DB répond. Utilisé par /health."""
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("DB ping failed: %s", exc)
        return False


@asynccontextmanager
async def lifespan_db():
    """Context manager pour startup/shutdown DB lifecycle."""
    logger.info("DB engine starting (url=%s)", DATABASE_URL.split("@")[-1])
    yield
    logger.info("DB engine disposing")
    await engine.dispose()