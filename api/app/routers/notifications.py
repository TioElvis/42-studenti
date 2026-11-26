"""Notifications: list, unread count, mark read, settings and browser push."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Response, status

from ..deps import CurrentUser, SessionDep, SettingsDep
from ..models.enums import NotificationType
from ..schemas.notification import (
    NotificationPage,
    NotificationSettings,
    NotificationSettingsUpdate,
    PushKey,
    PushSubscriptionIn,
    PushUnsubscribeIn,
    UnreadCount,
)
from ..services import notifications as notif_service
from ..services import push as push_service

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


@router.get("/push/key", response_model=PushKey)
async def push_key(user: CurrentUser, settings: SettingsDep) -> PushKey:
    return PushKey(public_key=settings.vapid_public_key if settings.push_configured else None)


@router.post("/push/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def push_subscribe(session: SessionDep, user: CurrentUser, data: PushSubscriptionIn) -> None:
    await push_service.subscribe(session, user_id=user.id, data=data)


@router.post("/push/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def push_unsubscribe(
    session: SessionDep, user: CurrentUser, data: PushUnsubscribeIn
) -> None:
    await push_service.unsubscribe(session, user_id=user.id, endpoint=data.endpoint)
