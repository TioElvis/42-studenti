"""La Bacheca: posts feed, detail, ownership-guarded CRUD, likes and sondaggi."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query, status

from ..deps import CurrentUser, SessionDep
from ..models.enums import PostCategory, PostType
from ..realtime import manager
from ..schemas.post import (
    LikeState,
    PollState,
    PollVoteIn,
    PostCreate,
    PostDetail,
    PostPage,
    PostUpdate,
    RsvpState,
)
from ..schemas.user import UserPublic
from ..services import notifications as notif_service
from ..services import posts as posts_service
from ..services import push as push_service

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=PostPage)
async def list_posts(
    session: SessionDep,
    user: CurrentUser,
    category: list[PostCategory] | None = Query(default=None),
    post_type: PostType | None = Query(default=None),
    q: str | None = Query(default=None, max_length=64),
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> PostPage:
    # ``category`` may be repeated (?category=a&category=b) for a multi-select.
    return await posts_service.list_posts(
        session,
        viewer_id=user.id,
        categories=category,
        post_type=post_type,
        q=q,
        cursor=cursor,
        limit=limit,
    )


@router.post("", response_model=PostDetail, status_code=status.HTTP_201_CREATED)
async def create_post(
    session: SessionDep, user: CurrentUser, data: PostCreate, background: BackgroundTasks
) -> PostDetail:
    created = await posts_service.create_post(session, author=user, data=data)
    detail = await posts_service.get_detail(session, post_id=created.id, viewer_id=user.id)
    await manager.broadcast("post.created", detail.model_dump(mode="json"))
    ids = await notif_service.create_post_notifications(
        session, post_id=created.id, author_id=user.id
    )
    background.add_task(push_service.deliver, ids)
    return detail


@router.get("/{post_id}", response_model=PostDetail)
async def get_post(session: SessionDep, user: CurrentUser, post_id: int) -> PostDetail:
    return await posts_service.get_detail(session, post_id=post_id, viewer_id=user.id)


@router.patch("/{post_id}", response_model=PostDetail)
async def update_post(
    session: SessionDep, user: CurrentUser, post_id: int, data: PostUpdate
) -> PostDetail:
    await posts_service.update_post(session, post_id=post_id, user_id=user.id, data=data)
    detail = await posts_service.get_detail(session, post_id=post_id, viewer_id=user.id)
    await manager.broadcast("post.updated", detail.model_dump(mode="json"))
    return detail


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(session: SessionDep, user: CurrentUser, post_id: int) -> None:
    await posts_service.delete_post(session, post_id=post_id, user_id=user.id)
    await manager.broadcast("post.deleted", {"id": post_id})


@router.post("/{post_id}/like", response_model=LikeState)
async def toggle_like(session: SessionDep, user: CurrentUser, post_id: int) -> LikeState:
    state = await posts_service.toggle_like(session, post_id=post_id, user_id=user.id)
    await manager.broadcast("post.like", {"post_id": post_id, "like_count": state.like_count})
    return state


@router.post("/{post_id}/rsvp", response_model=RsvpState)
async def toggle_rsvp(session: SessionDep, user: CurrentUser, post_id: int) -> RsvpState:
    state = await posts_service.toggle_rsvp(session, post_id=post_id, user_id=user.id)
    await manager.broadcast(
        "post.rsvp",
        {"post_id": post_id, "rsvp_count": state.rsvp_count, "rsvp_full": state.rsvp_full},
    )
    return state


@router.get("/{post_id}/attendees", response_model=list[UserPublic])
async def list_attendees(
    session: SessionDep, user: CurrentUser, post_id: int
) -> list[UserPublic]:
    return await posts_service.list_attendees(session, post_id=post_id)


@router.post("/{post_id}/poll/vote", response_model=PollState)
async def vote_poll(
    session: SessionDep, user: CurrentUser, post_id: int, data: PollVoteIn
) -> PollState:
    state = await posts_service.vote_poll(
        session, post_id=post_id, user_id=user.id, option_id=data.option_id
    )
    # Broadcast counts only (never per-viewer voted flags).
    await manager.broadcast(
        "post.poll_vote",
        {
            "post_id": post_id,
            "options": [{"id": o.id, "vote_count": o.vote_count} for o in state.options],
        },
    )
    return state
