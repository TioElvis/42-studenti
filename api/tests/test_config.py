"""The asyncpg URL sanitizer (Supabase pooler / pgbouncer handling)."""

from __future__ import annotations

from app.config import asyncpg_url_and_connect_args


def test_strips_pgbouncer_and_disables_stmt_cache():
    url, args = asyncpg_url_and_connect_args(
        "postgresql://u:p@db.supabase.co:6543/postgres?pgbouncer=true"
    )
    assert url == "postgresql+asyncpg://u:p@db.supabase.co:6543/postgres"
    assert "pgbouncer" not in url
    assert args == {"statement_cache_size": 0}


def test_translates_sslmode_to_ssl():
    _, args = asyncpg_url_and_connect_args(
        "postgresql+asyncpg://u:p@host.pooler.supabase.com:6543/postgres?sslmode=require"
    )
    assert args["ssl"] is True
    assert args["statement_cache_size"] == 0


def test_direct_connection_untouched():
    url, args = asyncpg_url_and_connect_args("postgresql://u:p@db.supabase.co:5432/postgres")
    assert url == "postgresql+asyncpg://u:p@db.supabase.co:5432/postgres"
    assert args == {}


def test_sqlite_untouched():
    url, args = asyncpg_url_and_connect_args("sqlite+aiosqlite:///./x.db")
    assert url == "sqlite+aiosqlite:///./x.db"
    assert args == {}


def test_github_repo_normalized():
    from app.config import Settings

    assert Settings(GITHUB_REPO="https://github.com/TioElvis/42-studenti").github_repo == (
        "TioElvis/42-studenti"
    )
    assert Settings(GITHUB_REPO="TioElvis/42-studenti.git/").github_repo == "TioElvis/42-studenti"
    assert Settings(GITHUB_REPO="").github_repo == ""
