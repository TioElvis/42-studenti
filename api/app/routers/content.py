"""Materiale / Archivio: read-only file content served from assets/."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse

from ..deps import CurrentUser, SettingsDep
from ..schemas.content import ContentFile, ContentList
from ..services import content as content_service

router = APIRouter(prefix="/content", tags=["content"])

# Media types safe to serve inline (rendered by the browser). Everything else
# (Office docs, archives, svg, …) is sent as an attachment.
_INLINE_MIME = {"application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp"}


def _cache(headers: dict[str, str], settings) -> None:
    headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"


@router.get("/{section}", response_model=ContentList)
async def list_content(
    section: str,
    response: Response,
    settings: SettingsDep,
    user: CurrentUser,
) -> ContentList:
    """List the files under a section (``material`` or ``archive``)."""
    result = content_service.list_entries(settings, section)
    response.headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"
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
    response.headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"
    return result


@router.get("/{section}/file")
async def serve_file(
    section: str,
    settings: SettingsDep,
    user: CurrentUser,
    path: str = Query(..., min_length=1, max_length=512),
    download: bool = Query(False),
) -> FileResponse:
    """Stream a file of any type. Images/PDFs are served inline (so the UI can
    render them); other types, or ``download=1``, are sent as an attachment."""
    target, mime = content_service.resolve_file(settings, section, path)
    inline = (not download) and (mime in _INLINE_MIME)
    headers: dict[str, str] = {
        "Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{target.name}"',
        "X-Content-Type-Options": "nosniff",
    }
    _cache(headers, settings)
    # The web app (a different origin) embeds inline PDFs in an <iframe>; scope
    # framing to the frontend only. Other responses stay un-framable.
    if inline and mime == "application/pdf":
        headers["Content-Security-Policy"] = f"frame-ancestors 'self' {settings.frontend_url}"
    else:
        headers["Content-Security-Policy"] = "default-src 'none'"
    return FileResponse(target, media_type=mime, headers=headers)
