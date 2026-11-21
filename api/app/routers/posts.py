"""La Bacheca: posts feed, detail, ownership-guarded CRUD, likes and sondaggi."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from ..deps import CurrentUser, SessionDep
from ..models.enums import PostCategory, PostType
from ..realtime import manager
from ..schemas.post import (
    LikeState,
    PostCreate,
    PostDetail,
    PostPage,
    PostUpdate,
    RsvpState,
)
from ..schemas.user import UserPublic
from ..services import posts as posts_service

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=PostPage)
async def list_posts(
    session: SessionDep,
    user: CurrentUser,
    category: PostCategory | None = Query(default=None),
    post_type: PostType | None = Query(default=None),
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> PostPage:
    return await posts_service.list_posts(
        session,
        viewer_id=user.id,
        category=category,
        post_type=post_type,
        cursor=cursor,
        limit=limit,
    )


@router.post("", response_model=PostDetail, status_code=status.HTTP_201_CREATED)
async def create_post(session: SessionDep, user: CurrentUser, data: PostCreate) -> PostDetail:
    created = await posts_service.create_post(session, author=user, data=data)
    detail = await posts_service.get_detail(session, post_id=created.id, viewer_id=user.id)
    await manager.broadcast("post.created", detail.model_dump(mode="json"))
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
