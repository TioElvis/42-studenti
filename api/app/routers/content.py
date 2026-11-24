"""Materiale / Archivio: read-only file content served from assets/."""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse

from ..deps import CurrentUser, SettingsDep
from ..schemas.content import ContentFile, ContentList
from ..services import content as content_service

router = APIRouter(prefix="/content", tags=["content"])


def _content_disposition(disposition: str, filename: str) -> str:
    """Build a safe Content-Disposition value (no header injection).

    A plain ASCII, quote/control-stripped ``filename`` for old clients plus an
    RFC 5987 ``filename*`` carrying the real (possibly non-ASCII) name.
    """
    ascii_name = re.sub(r'[\\"\r\n]+', "_", filename.encode("ascii", "ignore").decode()) or "file"
    return f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"

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
    result = await content_service.get_listing(settings, section)
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
    result = await content_service.get_text(settings, section, path)
    response.headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"
    return result


@router.get("/{section}/file")
async def serve_file(
    section: str,
    settings: SettingsDep,
    user: CurrentUser,
    path: str = Query(..., min_length=1, max_length=512),
    download: bool = Query(False),
) -> Response:
    """Stream a file of any type. Images/PDFs are served inline (so the UI can
    render them); other types, or ``download=1``, are sent as an attachment."""
    payload = await content_service.get_file(settings, section, path)
    mime = payload.media_type
    inline = (not download) and (mime in _INLINE_MIME)
    headers: dict[str, str] = {
        "Content-Disposition": _content_disposition(
            "inline" if inline else "attachment", payload.name
        ),
        "X-Content-Type-Options": "nosniff",
    }
    _cache(headers, settings)
    # The web app (a different origin) embeds inline PDFs in an <iframe>; scope
    # framing to the frontend only. Other responses stay un-framable.
    if inline and mime == "application/pdf":
        headers["Content-Security-Policy"] = f"frame-ancestors 'self' {settings.frontend_url}"
    else:
        headers["Content-Security-Policy"] = "default-src 'none'"
    # Local file → FileResponse (efficient); GitHub bytes → in-memory Response.
    if payload.path is not None:
        return FileResponse(payload.path, media_type=mime, headers=headers)
    return Response(content=payload.data or b"", media_type=mime, headers=headers)
