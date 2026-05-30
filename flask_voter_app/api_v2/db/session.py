"""
api_v2.db.session — async engine + session factory.

The engine is built lazily (first use), so importing this module never requires
the production driver (asyncpg) to be installed — handy for local dev/tests that
run on aiosqlite. The DB URL is read from Settings.database_url and normalised to
an async dialect:

    postgresql://…           → postgresql+asyncpg://…
    sqlite:///…              → sqlite+aiosqlite:///…

Tests override the engine via `set_engine()` with an in-memory aiosqlite engine.
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api_v2.core.config import get_settings


def to_async_url(url: str) -> str:
    """Normalise a sync SQLAlchemy URL to its async-driver equivalent."""
    if "+asyncpg" in url or "+aiosqlite" in url:
        return url
    if url.startswith("postgresql"):
        return url.replace("postgresql", "postgresql+asyncpg", 1)
    if url.startswith("sqlite"):
        return url.replace("sqlite", "sqlite+aiosqlite", 1)
    return url


_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, building it on first use."""
    global _engine
    if _engine is None:
        url = to_async_url(get_settings().database_url)
        _engine = create_async_engine(url, future=True, pool_pre_ping=True)
    return _engine


def set_engine(engine: AsyncEngine) -> None:
    """Swap the engine (tests inject an in-memory aiosqlite engine)."""
    global _engine, _session_maker
    _engine = engine
    _session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the session factory bound to the current engine."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_maker


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped async session."""
    async with async_session_maker()() as session:
        yield session
