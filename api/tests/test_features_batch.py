"""Backend for the 2026-11-21 feature batch: comment replies and the sondaggi
(post_type) filter."""

from __future__ import annotations

import pytest

from app.database import get_sessionmaker
from app.models.enums import PostCategory, PostType
from app.schemas.comment import CommentCreate
from app.schemas.post import PostCreate
from app.services import posts as posts_svc
from app.services.exceptions import NotFoundError


async def _post(session, author, text, *, category=PostCategory.OFF_TOPIC, post_type=PostType.POST):
    return await posts_svc.create_post(
        session,
        author=author,
        data=PostCreate(title="Titolo", content=text, category=category, post_type=post_type),
    )


# ---- Comment replies (#5) ----


async def test_reply_sets_ref_to_parent_author(engine, users):
    alice, bob = users["alice"], users["bob"]
    maker = get_sessionmaker()
    async with maker() as s:
        post = await _post(s, alice, "ciao")
    async with maker() as s:
        parent = await posts_svc.add_comment(
            s, post_id=post.id, author=alice, data=CommentCreate(content="primo")
        )
    async with maker() as s:
        reply = await posts_svc.add_comment(
            s, post_id=post.id, author=bob,
            data=CommentCreate(content="risposta", parent_id=parent.id),
        )
    assert reply.parent_id == parent.id
    assert reply.reply_to == "alice"  # the @ref points at the parent's author

    async with maker() as s:
        detail = await posts_svc.get_detail(s, post_id=post.id, viewer_id=bob.id)
    threaded = [c for c in detail.comments if c.parent_id is not None]
    assert threaded and threaded[0].reply_to == "alice"


async def test_reply_to_comment_on_another_post_rejected(engine, users):
    alice = users["alice"]
    maker = get_sessionmaker()
    async with maker() as s:
        p1 = await _post(s, alice, "a")
        p2 = await _post(s, alice, "b")
    async with maker() as s:
        c1 = await posts_svc.add_comment(
            s, post_id=p1.id, author=alice, data=CommentCreate(content="x")
        )
    async with maker() as s:
        with pytest.raises(NotFoundError):
            await posts_svc.add_comment(
                s, post_id=p2.id, author=alice,
                data=CommentCreate(content="y", parent_id=c1.id),
            )


# ---- Sondaggi filter (#2 / #3) ----


async def test_list_posts_filters_by_type(engine, users):
    alice = users["alice"]
    maker = get_sessionmaker()
    async with maker() as s:
        await _post(s, alice, "normale")
        await _post(s, alice, "comunita", category=PostCategory.EVENTO_CASUALE,
                    post_type=PostType.SONDAGGIO)
    async with maker() as s:
        only_polls = await posts_svc.list_posts(
            s, viewer_id=alice.id, post_type=PostType.SONDAGGIO
        )
        everything = await posts_svc.list_posts(s, viewer_id=alice.id)
    assert [p.post_type for p in only_polls.items] == [PostType.SONDAGGIO]
    assert len(everything.items) == 2
