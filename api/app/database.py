"""Async SQLAlchemy engine and session factory.

The engine is created lazily from settings so tests can point it at an
in-memory SQLite database before the app imports anything heavy.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.async_database_url()
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. Copy api/.env.example to api/.env and fill it in."
            )
        _engine = create_async_engine(
            url,
            pool_pre_ping=True,
            future=True,
            connect_args=settings.async_connect_args(),
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, autoflush=False
        )
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session and always closes it."""
    maker = get_sessionmaker()
    async with maker() as session:
        yield session


def configure_engine(engine: AsyncEngine) -> None:
    """Test hook: inject a pre-built engine (e.g. SQLite) and reset the maker."""
    global _engine, _sessionmaker
    _engine = engine
    _sessionmaker = async_sessionmaker(
        bind=engine, expire_on_commit=False, autoflush=False
    )
