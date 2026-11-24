"""Shared test fixtures: in-memory SQLite, seeded users, ASGI client."""

from __future__ import annotations

import os
from dataclasses import dataclass

import pytest
import pytest_asyncio

# Configure required settings BEFORE the app imports them.
os.environ.setdefault("ENV", "development")
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production-use-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("FORTY_TWO_UID", "test-uid")
os.environ.setdefault("FORTY_TWO_SECRET", "test-secret")
# Force a known campus id so tests don't pick up a developer's local .env.
os.environ["FORTY_TWO_CAMPUS_ID"] = "61"
# Keep GitHub integration off in tests regardless of the maintainer's .env
# (tests that exercise it pass their own settings object).
os.environ["GITHUB_REPO"] = ""
os.environ["GITHUB_OAUTH_CLIENT_ID"] = ""
os.environ["GITHUB_OAUTH_SECRET"] = ""

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import configure_engine, get_sessionmaker  # noqa: E402
from app.deps import get_current_user  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base, User  # noqa: E402

get_settings.cache_clear()


@dataclass
class AuthContext:
    """Lets a test choose which seeded user is 'logged in'."""

    current: User


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    configure_engine(eng)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def users(engine) -> dict[str, User]:
    maker = get_sessionmaker()
    async with maker() as session:
        alice = User(intra_id=1001, login="alice", email="alice@42roma.it", display_name="Alice")
        bob = User(intra_id=1002, login="bob", email="bob@42roma.it", display_name="Bob")
        session.add_all([alice, bob])
        await session.commit()
        await session.refresh(alice)
        await session.refresh(bob)
    return {"alice": alice, "bob": bob}


@pytest_asyncio.fixture
async def client(engine, users):
    app = create_app()
    ctx = AuthContext(current=users["alice"])

    async def _override_current_user() -> User:
        # Re-load within the request's context to keep it attached to a session.
        maker = get_sessionmaker()
        async with maker() as session:
            return await session.get(User, ctx.current.id)

    app.dependency_overrides[get_current_user] = _override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.auth_ctx = ctx  # type: ignore[attr-defined]
        yield c
