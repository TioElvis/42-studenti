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
