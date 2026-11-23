"""Student search by login / display name."""

from __future__ import annotations

from app.database import get_sessionmaker
from app.services import students as students_svc


async def test_search_by_login(engine, users):
    async with get_sessionmaker()() as s:
        res = await students_svc.search(s, q="ali", limit=20)
    assert [u.login for u in res] == ["alice"]


async def test_search_by_display_name(engine, users):
    async with get_sessionmaker()() as s:
        res = await students_svc.search(s, q="Bob", limit=20)
    assert [u.login for u in res] == ["bob"]


async def test_short_query_returns_empty(engine, users):
    async with get_sessionmaker()() as s:
        assert await students_svc.search(s, q="a", limit=20) == []
        assert await students_svc.search(s, q="  ", limit=20) == []


async def test_wildcards_are_escaped(engine, users):
    async with get_sessionmaker()() as s:
        # "%%" must not match everything — it's treated literally.
        assert await students_svc.search(s, q="%%", limit=20) == []
