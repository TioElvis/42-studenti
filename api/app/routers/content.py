"""Materiale / Archivio: read-only file content served from assets/."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response

from ..deps import CurrentUser, SettingsDep
from ..schemas.content import ContentFile, ContentList
from ..services import content as content_service

router = APIRouter(prefix="/content", tags=["content"])


def _cache(response: Response, settings) -> None:
    # Content changes rarely (git commits); let clients cache it briefly.
    response.headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"


@router.get("/{section}", response_model=ContentList)
async def list_content(
    section: str,
    response: Response,
    settings: SettingsDep,
    user: CurrentUser,
) -> ContentList:
    """List the files under a section (``material`` or ``archive``)."""
    result = content_service.list_entries(settings, section)
    _cache(response, settings)
    return result


@router.get("/{section}/raw", response_model=ContentFile)
async def read_content(
    section: str,
    response: Response,
    settings: SettingsDep,
    user: CurrentUser,
    path: str = Query(..., min_length=1, max_length=512),
) -> ContentFile:
    """Return one text document's content (path is confined to the section root)."""
    result = content_service.read_file(settings, section, path)
    _cache(response, settings)
    return result
