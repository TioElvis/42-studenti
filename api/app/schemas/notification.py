"""Notification DTOs + notification settings."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator

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


# The server POSTs to the subscription endpoint, which the client supplies, so
# only the browsers' own push services are accepted (no SSRF).
_PUSH_HOSTS = {"fcm.googleapis.com"}  # Chrome, Brave, Opera, ...
_PUSH_HOST_SUFFIXES = (
    ".push.services.mozilla.com",  # Firefox
    ".notify.windows.com",  # Edge
    ".push.apple.com",  # Safari
)
_BASE64URL = r"^[A-Za-z0-9_-]+={0,2}$"


def _check_push_endpoint(value: str) -> str:
    # Printable ASCII without backslashes: URL parsers disagree on anything else.
    if not all("!" <= ch <= "~" and ch != "\\" for ch in value):
        raise ValueError("Endpoint push non valido.")
    parts = urlsplit(value)
    host = parts.netloc.lower()  # a port or userinfo makes the match fail
    if parts.scheme != "https" or not (
        host in _PUSH_HOSTS or host.endswith(_PUSH_HOST_SUFFIXES)
    ):
        raise ValueError("Endpoint push non valido.")
    if any(ch in host for ch in "@:"):
        raise ValueError("Endpoint push non valido.")
    return value


class PushKey(BaseModel):
    # None when Web Push is not configured on this server.
    public_key: str | None


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=80, max_length=128, pattern=_BASE64URL)
    auth: str = Field(min_length=16, max_length=64, pattern=_BASE64URL)


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(max_length=1024)
    keys: PushKeys
    lang: Literal["it", "en"] = "it"

    _valid_endpoint = field_validator("endpoint")(_check_push_endpoint)


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(max_length=1024)
