"""Notification DTOs + notification settings."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..models.enums import PostNotify
from .user import UserPublic


class NotificationOut(BaseModel):
    id: int
    type: str  # post | comment | reply | follow
    actor: UserPublic
    post_id: int | None
    is_read: bool
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    next_cursor: int | None = None
    unread: int


class UnreadCount(BaseModel):
    unread: int


class NotificationSettings(BaseModel):
    notify_posts: PostNotify
    notify_comments: bool
    notify_follows: bool


class NotificationSettingsUpdate(BaseModel):
    notify_posts: PostNotify | None = None
    notify_comments: bool | None = None
    notify_follows: bool | None = None
