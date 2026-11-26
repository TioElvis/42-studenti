"""Web Push: store browser subscriptions and deliver notifications to them."""

from __future__ import annotations

import asyncio
import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import Settings, get_settings
from ..database import get_sessionmaker
from ..models.enums import NotificationType
from ..models.notification import Notification
from ..models.push_subscription import PushSubscription
from ..schemas.notification import PushSubscriptionIn

logger = logging.getLogger("app.push")

# Browsers kept per student; the oldest are dropped beyond this.
MAX_SUBSCRIPTIONS_PER_USER = 10
# How long a push service keeps a message for an offline browser.
_TTL_SECONDS = 24 * 3600
_TIMEOUT_SECONDS = 10
_CONCURRENCY = 10
# Push service answers meaning "this subscription no longer exists".
_GONE = {404, 410}

_TEXT: dict[str, dict[NotificationType, str]] = {
    "it": {
        NotificationType.POST: "{actor} ha pubblicato un post",
        NotificationType.COMMENT: "{actor} ha commentato un tuo post",
        NotificationType.REPLY: "{actor} ha risposto a un tuo commento",
        NotificationType.FOLLOW: "{actor} ha iniziato a seguirti",
    },
    "en": {
        NotificationType.POST: "{actor} published a post",
        NotificationType.COMMENT: "{actor} commented on your post",
        NotificationType.REPLY: "{actor} replied to your comment",
        NotificationType.FOLLOW: "{actor} started following you",
    },
}


async def subscribe(session: AsyncSession, *, user_id: int, data: PushSubscriptionIn) -> None:
    """Save this browser for ``user_id``. An already known endpoint is updated and
    moves to the caller (another student logged in on the same browser)."""
    sub = await session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == data.endpoint)
    )
    if sub is None:
        sub = PushSubscription(endpoint=data.endpoint)
        session.add(sub)
    sub.user_id = user_id
    sub.p256dh = data.keys.p256dh
    sub.auth = data.keys.auth
    sub.lang = data.lang
    await session.flush()

    stale = await session.scalars(
        select(PushSubscription.id)
        .where(PushSubscription.user_id == user_id, PushSubscription.id != sub.id)
        .order_by(PushSubscription.id.desc())
        .offset(MAX_SUBSCRIPTIONS_PER_USER - 1)
    )
    stale_ids = list(stale)
    if stale_ids:
        await session.execute(delete(PushSubscription).where(PushSubscription.id.in_(stale_ids)))
    await session.commit()


async def unsubscribe(session: AsyncSession, *, user_id: int, endpoint: str) -> None:
    """Forget one of the caller's browsers (a no-op for anyone else's)."""
    await session.execute(
        delete(PushSubscription).where(
            PushSubscription.user_id == user_id, PushSubscription.endpoint == endpoint
        )
    )
    await session.commit()


def _payload(notification: Notification, lang: str) -> str:
    login = notification.actor.login
    if notification.type == NotificationType.FOLLOW:
        url = f"/u/{login}"
    elif notification.post_id is not None:
        url = f"/?post={notification.post_id}"
    else:
        url = "/"
    text = _TEXT.get(lang, _TEXT["it"])[notification.type]
    return json.dumps(
        {
            "title": "42 Studenti",
            "body": text.format(actor=f"@{login}"),
            "url": url,
            "tag": f"notification-{notification.id}",
        }
    )


def _send(settings: Settings, subscription: dict, payload: str) -> None:
    """Blocking send of one message (run it in a thread)."""
    webpush(
        subscription_info=subscription,
        data=payload,
        vapid_private_key=settings.vapid_private_key,
        # A fresh dict each time: pywebpush writes the audience into it.
        vapid_claims={"sub": settings.vapid_subject},
        ttl=_TTL_SECONDS,
        timeout=_TIMEOUT_SECONDS,
    )


async def deliver(notification_ids: list[int]) -> None:
    """Push the given notifications to their recipients' browsers.

    Meant to run after the response is sent, so it opens its own sessions and
    never raises. Subscriptions the push service reports as gone are deleted.
    """
    settings = get_settings()
    if not settings.push_configured or not notification_ids:
        return
    try:
        maker = get_sessionmaker()
        async with maker() as session:
            rows = await session.execute(
                select(Notification, PushSubscription)
                .join(PushSubscription, PushSubscription.user_id == Notification.recipient_id)
                .options(selectinload(Notification.actor))
                .where(Notification.id.in_(notification_ids))
            )
            jobs = [
                (
                    sub.id,
                    {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                    _payload(notification, sub.lang),
                )
                for notification, sub in rows.all()
            ]

        limit = asyncio.Semaphore(_CONCURRENCY)

        async def _one(sub_id: int, subscription: dict, payload: str) -> int | None:
            async with limit:
                try:
                    await asyncio.to_thread(_send, settings, subscription, payload)
                except WebPushException as exc:
                    code = getattr(exc.response, "status_code", None)
                    if code in _GONE:
                        return sub_id
                    # The message is left out: it can contain the endpoint.
                    logger.warning("Push rejected (subscription %s, status %s)", sub_id, code)
                except Exception as exc:  # noqa: BLE001 - one bad send must not stop the rest
                    logger.warning(
                        "Push failed (subscription %s, %s)", sub_id, type(exc).__name__
                    )
            return None

        gone = [i for i in await asyncio.gather(*(_one(*job) for job in jobs)) if i is not None]
        if gone:
            async with maker() as session:
                await session.execute(
                    delete(PushSubscription).where(PushSubscription.id.in_(gone))
                )
                await session.commit()
    except Exception:  # noqa: BLE001 - background task: log and move on
        logger.exception("Push delivery failed")
