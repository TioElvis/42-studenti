"""Follow / unfollow another student."""

from __future__ import annotations

from fastapi import APIRouter, Path, status

from ..deps import CurrentUser, SessionDep
from ..services import follows as follows_service
from ..services import notifications as notif_service

router = APIRouter(prefix="/users", tags=["follows"])


@router.post("/{login}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_user(
    session: SessionDep,
    user: CurrentUser,
    login: str = Path(..., min_length=1, max_length=64),
) -> None:
    target, created = await follows_service.follow(session, follower=user, login=login)
    if created:
        await notif_service.create_follow_notification(session, followee=target, actor_id=user.id)


@router.delete("/{login}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    session: SessionDep,
    user: CurrentUser,
    login: str = Path(..., min_length=1, max_length=64),
) -> None:
    await follows_service.unfollow(session, follower=user, login=login)
