"""Notifications: list, unread count, mark read, and notification settings."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response, status

from ..deps import CurrentUser, SessionDep
from ..schemas.notification import (
    NotificationPage,
    NotificationSettings,
    NotificationSettingsUpdate,
    UnreadCount,
)
from ..services import notifications as notif_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationPage)
async def list_notifications(
    session: SessionDep,
    user: CurrentUser,
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
) -> NotificationPage:
    return await notif_service.list_notifications(
        session, user_id=user.id, cursor=cursor, limit=limit
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
