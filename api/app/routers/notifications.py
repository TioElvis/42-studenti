"""Notifications: list, unread count, mark read, and notification settings."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Response, status

from ..deps import CurrentUser, SessionDep
from ..models.enums import NotificationType
from ..schemas.notification import (
    NotificationPage,
    NotificationSettings,
    NotificationSettingsUpdate,
    UnreadCount,
)
from ..services import notifications as notif_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

# UI filter tabs -> the notification types they cover (empty = no type filter).
_FILTER_KINDS: dict[str, set[NotificationType]] = {
    "all": set(),
    "posts": {NotificationType.POST},
    "comments": {NotificationType.COMMENT, NotificationType.REPLY},
    "follows": {NotificationType.FOLLOW},
}


@router.get("", response_model=NotificationPage)
async def list_notifications(
    session: SessionDep,
    user: CurrentUser,
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    filter: Literal["all", "posts", "comments", "follows"] = Query(default="all"),
) -> NotificationPage:
    return await notif_service.list_notifications(
        session,
        user_id=user.id,
        cursor=cursor,
        limit=limit,
        kinds=_FILTER_KINDS[filter] or None,
    )


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    session: SessionDep, user: CurrentUser, response: Response
) -> UnreadCount:
    response.headers["Cache-Control"] = "no-store"
    return UnreadCount(unread=await notif_service.unread_count(session, user.id))


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all(session: SessionDep, user: CurrentUser) -> None:
    await notif_service.mark_all_read(session, user.id)


@router.get("/settings", response_model=NotificationSettings)
async def get_settings(user: CurrentUser) -> NotificationSettings:
    return notif_service.settings_of(user)


@router.patch("/settings", response_model=NotificationSettings)
async def update_settings(
    session: SessionDep, user: CurrentUser, data: NotificationSettingsUpdate
) -> NotificationSettings:
    return await notif_service.update_settings(session, user=user, data=data)
