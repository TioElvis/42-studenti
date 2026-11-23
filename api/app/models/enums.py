"""Domain enums shared by models and schemas.

Category values are stable slugs; the Italian/romanesco display labels live in
the frontend (web/src/lib/categories.ts). Keeping slugs here avoids accents and
spaces in the database enum and lets the UI own presentation.
"""

from __future__ import annotations

import enum


class PostCategory(str, enum.Enum):
    STUDIO = "studio"
    CERCO_TEAM = "cerco_team"
    EVENTO_CASUALE = "evento_casuale"
    VITA_ROMANA = "vita_romana"
    MERCATINO = "mercatino"
    OFF_TOPIC = "off_topic"


class PostType(str, enum.Enum):
    """A plain message, or a 'sondaggio' with an attendance tracker."""

    POST = "post"
    SONDAGGIO = "sondaggio"


class NotificationType(str, enum.Enum):
    POST = "post"  # a new post (from someone you follow, or anyone)
    COMMENT = "comment"  # someone commented on your post
    REPLY = "reply"  # someone replied to your comment
    FOLLOW = "follow"  # someone started following you


class PostNotify(str, enum.Enum):
    """How a student wants to be notified about new posts."""

    OFF = "off"
    FOLLOWED = "followed"  # only posts from people they follow
    ALL = "all"
