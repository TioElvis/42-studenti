"""Comment threads: create under a post, delete your own."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status

from ..deps import CurrentUser, SessionDep
from ..realtime import manager
from ..schemas.comment import CommentCreate, CommentOut
from ..services import notifications as notif_service
from ..services import posts as posts_service
from ..services import push as push_service

router = APIRouter(tags=["comments"])


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    session: SessionDep,
    user: CurrentUser,
    post_id: int,
    data: CommentCreate,
    background: BackgroundTasks,
) -> CommentOut:
    comment = await posts_service.add_comment(session, post_id=post_id, author=user, data=data)
    ids = await notif_service.create_comment_notifications(
        session, post_id=post_id, actor_id=user.id, parent_comment_id=data.parent_id
    )
    background.add_task(push_service.deliver, ids)
    count = await posts_service.comment_count(session, post_id)
    await manager.broadcast(
        "comment.created",
        {
            "post_id": post_id,
            "comment_count": count,
            "comment": comment.model_dump(mode="json"),
        },
    )
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(session: SessionDep, user: CurrentUser, comment_id: int) -> None:
    post_id = await posts_service.delete_comment(session, comment_id=comment_id, user_id=user.id)
    count = await posts_service.comment_count(session, post_id)
    await manager.broadcast(
        "comment.deleted",
        {"post_id": post_id, "comment_id": comment_id, "comment_count": count},
    )
