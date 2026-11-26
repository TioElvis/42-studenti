"""Student profile: 42-driven identity + campus gate, with in-app activity."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.database import get_sessionmaker
from app.intra import EventsUnavailableError, IntraUserInfo, IntraUserNotFound, ProjectInfo
from app.models.enums import PostCategory
from app.models.user import User
from app.schemas.comment import CommentCreate
from app.schemas.post import PostCreate
from app.services import posts as posts_svc
from app.services import profile as profile_svc
from app.services.exceptions import NotFoundError

CAMPUS = 61  # conftest forces FORTY_TWO_CAMPUS_ID=61


def _info(login="alice", campus_ids=frozenset({CAMPUS}), **over) -> IntraUserInfo:
    base = dict(
        login=login,
        display_name="Alice 42",
        avatar_url="https://cdn.intra.42.fr/alice.jpg",
        campus="Rome",
        campus_ids=campus_ids,
        level=7.42,
        grade="Member",
        correction_point=9,
        wallet=100,
        location="c1r2p3",
        pool="Set 2024",
        joined=None,
        projects=(),
        achievements=(),
    )
    base.update(over)
    return IntraUserInfo(**base)


class _Provider:
    """Stub: returns a fixed IntraUserInfo, or raises if given an Exception."""

    def __init__(self, result):
        self._result = result

    async def user_profile(self, login: str):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


async def _post(session, author, text):
    return await posts_svc.create_post(
        session, author=author, data=PostCreate(title="Titolo", content=text, category=PostCategory.OFF_TOPIC)
    )


async def test_own_profile_identity_from_42_and_activity(engine, users):
    alice, bob = users["alice"], users["bob"]
    maker = get_sessionmaker()
    async with maker() as s:
        (await s.get(User, alice.id)).login_count = 7
        await s.commit()
    async with maker() as s:
        p1 = await _post(s, alice, "uno")
        await _post(s, alice, "due")
        bob_post = await _post(s, bob, "x")
    async with maker() as s:
        await posts_svc.toggle_like(s, post_id=p1.id, user_id=bob.id)  # alice gets 1 daje
        await posts_svc.add_comment(
            s, post_id=bob_post.id, author=alice, data=CommentCreate(content="ciao")
        )
    info = _info(
        projects=(ProjectInfo(name="libft", status="finished", mark=125, validated=True),),
        achievements=("Welcome",),
    )
    async with maker() as s:
        prof = await profile_svc.get_profile(
            s, settings=get_settings(), provider=_Provider(info), viewer=alice, login="alice"
        )

    assert prof.is_me is True
    assert prof.display_name == "Alice 42" and prof.campus == "Rome"  # from 42, not DB
    assert prof.intra.level == 7.42 and prof.intra.wallet == 100
    assert prof.intra.grade == "Member"
    assert prof.intra.projects[0].name == "libft" and prof.intra.projects[0].validated is True
    assert prof.intra.achievements == ["Welcome"]
    assert prof.activity.posts == 2 and prof.activity.daje_received == 1
    assert prof.activity.comments == 1 and prof.activity.logins == 7


async def test_other_campus_is_404(engine, users):
    async with get_sessionmaker()() as s:
        with pytest.raises(NotFoundError):
            await profile_svc.get_profile(
                s, settings=get_settings(),
                provider=_Provider(_info(campus_ids=frozenset({1}))),  # Paris, not 42 Roma
                viewer=users["bob"], login="alice",
            )


async def test_unknown_42_login_is_404(engine, users):
    async with get_sessionmaker()() as s:
        with pytest.raises(NotFoundError):
            await profile_svc.get_profile(
                s, settings=get_settings(), provider=_Provider(IntraUserNotFound("ghost")),
                viewer=users["alice"], login="ghost",
            )


async def test_42_unavailable_propagates(engine, users):
    async with get_sessionmaker()() as s:
        with pytest.raises(EventsUnavailableError):
            await profile_svc.get_profile(
                s, settings=get_settings(), provider=_Provider(EventsUnavailableError("down")),
                viewer=users["alice"], login="alice",
            )


async def test_42roma_student_without_app_account_has_zero_activity(engine, users):
    # A 42 Roma student who never used the app: viewable, activity all zeros.
    async with get_sessionmaker()() as s:
        prof = await profile_svc.get_profile(
            s, settings=get_settings(), provider=_Provider(_info(login="newbie")),
            viewer=users["alice"], login="newbie",
        )
    assert prof.is_me is False and prof.activity.posts == 0 and prof.activity.logins == 0
