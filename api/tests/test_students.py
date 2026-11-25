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


async def _add_many(n: int):
    from app.models.user import User

    async with get_sessionmaker()() as s:
        s.add_all(
            User(intra_id=2000 + i, login=f"stud{i:02d}", display_name=f"Studente {i}")
            for i in range(n)
        )
        await s.commit()


async def test_page_lists_everyone_when_no_query(engine, users):
    await _add_many(25)  # + alice, bob = 27
    async with get_sessionmaker()() as s:
        p1 = await students_svc.list_page(s, page=1, page_size=10)
        p3 = await students_svc.list_page(s, page=3, page_size=10)
    assert (p1.total, p1.pages, p1.page, len(p1.items)) == (27, 3, 1, 10)
    assert [u.login for u in p1.items][:2] == ["alice", "bob"]  # ordered by login
    assert (p3.page, len(p3.items)) == (3, 7)


async def test_page_is_clamped_to_last(engine, users):
    async with get_sessionmaker()() as s:
        p = await students_svc.list_page(s, page=99, page_size=10)
        z = await students_svc.list_page(s, page=0, page_size=10)
    assert p.page == 1 and p.pages == 1 and len(p.items) == 2
    assert z.page == 1


async def test_page_filter_and_short_query(engine, users):
    await _add_many(25)
    async with get_sessionmaker()() as s:
        f = await students_svc.list_page(s, q="stud1", page=1, page_size=5)
        short = await students_svc.list_page(s, q="a", page=1, page_size=50)
        wild = await students_svc.list_page(s, q="%%", page=1, page_size=50)
    assert f.total == 10 and f.pages == 2 and all(u.login.startswith("stud1") for u in f.items)
    assert short.total == 27  # 1 char → ignored, lists everyone
    assert wild.total == 0  # wildcards are literal


async def test_page_endpoint(client):
    r = await client.get("/students/page?page_size=1&page=2")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2 and body["pages"] == 2 and body["page"] == 2
    assert [u["login"] for u in body["items"]] == ["bob"]
    assert (await client.get("/students/page?page_size=500")).status_code == 422
