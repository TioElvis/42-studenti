"""Alembic environment — async engine, URL from the environment.

Uses DIRECT_URL (a direct 5432 connection, recommended for migrations against
Supabase/pgbouncer) and falls back to DATABASE_URL. Both are coerced to the
asyncpg driver so no extra DB driver is required.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import asyncpg_url_and_connect_args, get_settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url_and_args() -> tuple[str, dict]:
    settings = get_settings()
    raw = settings.direct_url or settings.database_url
    if not raw:
        raise RuntimeError(
            "No database URL. Set DIRECT_URL (preferred) or DATABASE_URL in api/.env."
        )
    return asyncpg_url_and_connect_args(raw)


def run_migrations_offline() -> None:
    url, _ = _database_url_and_args()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url, connect_args = _database_url_and_args()
    connectable = create_async_engine(url, poolclass=NullPool, connect_args=connect_args)
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
