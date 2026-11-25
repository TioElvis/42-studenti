"""Link a student's GitHub account and contribute files to assets/ by direct commit.

The link flow mirrors the 42 OAuth flow (state-cookie CSRF, server-side code
exchange). Contributions are confined to assets/<section>/ and run with the
student's own encrypted token — never the maintainer's.
"""

from __future__ import annotations

import base64
import binascii
import hmac
import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse

from .. import github_user
from ..deps import CurrentUser, SessionDep, SettingsDep
from ..ratelimit import auth_rate_limiter, upload_limiter
from ..schemas.github import ContributeIn, ContributeOut, DeleteIn, DeleteOut, GithubStatus
from ..services import content as content_service
from ..services import upload_guard
from ..services.exceptions import NotFoundError

logger = logging.getLogger("app.github")

router = APIRouter(prefix="/github", tags=["github"])

_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_STATE_COOKIE = "github_state"
_MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5 MiB


@router.get("/status", response_model=GithubStatus)
async def status_(settings: SettingsDep, user: CurrentUser) -> GithubStatus:
    special = settings.is_special_user(user.login)
    return GithubStatus(
        configured=settings.github_contrib_configured,
        server_mode=settings.github_server_writes,
        linked=bool(user.github_username),
        username=user.github_username,
        can_archive=special,
        can_delete=special,
    )


@router.get("/link", dependencies=[Depends(auth_rate_limiter)])
async def link(settings: SettingsDep, user: CurrentUser) -> RedirectResponse:
    if not settings.github_oauth_configured:
        return _frontend_redirect(settings, "github=unavailable")
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.github_oauth_client_id,
        "redirect_uri": settings.github_oauth_callback_url,
        "scope": "public_repo",
        "state": state,
    }
    resp = RedirectResponse(
        url=f"{_AUTHORIZE_URL}?{urlencode(params)}", status_code=status.HTTP_302_FOUND
    )
    resp.set_cookie(
        key=_STATE_COOKIE,
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/github",
    )
    return resp


@router.get("/link/callback", dependencies=[Depends(auth_rate_limiter)])
async def link_callback(
    request: Request,
    settings: SettingsDep,
    session: SessionDep,
    user: CurrentUser,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error or not code or not state:
        return _frontend_redirect(settings, "github=error")
    expected = request.cookies.get(_STATE_COOKIE)
    if not expected or not hmac.compare_digest(expected, state):
        return _frontend_redirect(settings, "github=error")
    try:
        token = await github_user.exchange_oauth_code(settings, code)
        login = await github_user.fetch_github_login(token)
    except (github_user.GithubAuthRequired, github_user.GithubApiError):
        logger.warning("GitHub link failed during token/profile exchange")
        return _frontend_redirect(settings, "github=error")

    github_user.apply_github_token(user, token=token, username=login)
    await session.commit()
    resp = _frontend_redirect(settings, "github=linked")
    resp.delete_cookie(_STATE_COOKIE, path="/github")
    return resp


@router.delete("/link", status_code=status.HTTP_204_NO_CONTENT)
async def unlink(session: SessionDep, user: CurrentUser) -> None:
    github_user.clear_github(user)
    await session.commit()


@router.post("/contribute", response_model=ContributeOut)
async def contribute(
    session: SessionDep,
    user: CurrentUser,
    settings: SettingsDep,
    data: ContributeIn,
) -> ContributeOut:
    if not settings.github_contrib_configured:
        raise HTTPException(status_code=503, detail="Contributi GitHub non disponibili.")

    upload_limiter.check_key(f"user:{user.id}")  # 20 contributions / 10 min / student
    if not content_service.section_allowed(data.section):
        raise HTTPException(status_code=404, detail="Sezione non valida.")
    # The archive section is restricted to the special users (42 logins).
    if data.section == "archive" and not settings.is_special_user(user.login):
        raise HTTPException(
            status_code=403, detail="Solo gli utenti speciali possono contribuì all'archivio."
        )

    # In server-token mode the backend commits for everyone (no per-student link
    # needed); otherwise the student must have linked their own GitHub.
    server = settings.github_server_writes
    student_token = github_user.github_token_of(user)
    if not server and (not student_token or not user.github_username):
        raise HTTPException(status_code=409, detail="Collega prima il tuo account GitHub.")

    try:
        if data.create_folder:
            rel = content_service.keep_path(data.path)  # <folder>/.gitkeep
        else:
            rel = content_service.confine_rel(data.path)  # never escapes assets/<section>/
    except NotFoundError as exc:
        raise HTTPException(status_code=400, detail="Percorso non valido.") from exc

    # Normalize the body to base64 and enforce the size cap.
    if data.create_folder:
        content_b64 = ""  # empty .gitkeep
    elif not data.content:
        raise HTTPException(status_code=400, detail="Contenuto mancante.")
    elif data.encoding == "base64":
        try:
            raw = base64.b64decode(data.content, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Contenuto base64 non valido.") from exc
        content_b64 = data.content
    else:
        raw = data.content.encode("utf-8")
        content_b64 = base64.b64encode(raw).decode("ascii")
    if not data.create_folder and len(raw) > _MAX_CONTENT_BYTES:
        raise HTTPException(status_code=413, detail="File troppo grande (max 5 MiB).")
    if not data.create_folder:
        # Safety checks before anything is committed: name, extension, real content.
        try:
            upload_guard.validate_upload(rel, raw)
        except upload_guard.UploadRejected as exc:
            raise HTTPException(status_code=exc.status, detail=exc.detail) from exc

    message = (data.message or "").strip() or None  # default Add/Update set on commit
    try:
        if server:
            who = user.github_username or user.login
            url, action = await github_user.contribute_server(
                settings=settings,
                section=data.section,
                rel_path=rel,
                content_b64=content_b64,
                message=message,
                author_name=user.github_username or user.display_name or user.login,
                author_login=who,
            )
        else:
            url, action = await github_user.contribute_direct_push(
                settings=settings,
                token=student_token,
                section=data.section,
                rel_path=rel,
                content_b64=content_b64,
                message=message,
            )
    except github_user.GithubAuthRequired as exc:
        raise HTTPException(
            status_code=409,
            detail="GitHub ha negato l'operazione (serve accesso in scrittura, o ricollega).",
        ) from exc
    except github_user.GithubApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc) or "GitHub ha rifiutato.") from exc

    # The branch changed → drop the cached listing so the change shows at once.
    content_service.invalidate_github_cache(data.section)
    return ContributeOut(url=url, action=action)  # type: ignore[arg-type]


@router.post("/delete", response_model=DeleteOut)
async def delete_content(
    user: CurrentUser,
    settings: SettingsDep,
    data: DeleteIn,
) -> DeleteOut:
    """Delete a file or a whole folder under assets/<section>/ (special users only)."""
    if not settings.github_contrib_configured:
        raise HTTPException(status_code=503, detail="Contributi GitHub non disponibili.")
    # Authorization first, server-side: only GITHUB_SPECIAL_USERS may delete.
    if not settings.is_special_user(user.login):
        raise HTTPException(status_code=403, detail="Solo gli utenti speciali possono elimina'.")
    if not content_service.section_allowed(data.section):
        raise HTTPException(status_code=404, detail="Sezione non valida.")

    server = settings.github_server_writes
    student_token = github_user.github_token_of(user)
    if not server and not student_token:
        raise HTTPException(status_code=409, detail="Collega prima il tuo account GitHub.")

    try:
        rel = (
            content_service.confine_folder(data.path)
            if data.folder
            else content_service.confine_rel(data.path)
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=400, detail="Percorso non valido.") from exc

    who = user.github_username or user.login
    try:
        url = await github_user.delete_path(
            settings=settings,
            token=None if server else student_token,
            section=data.section,
            rel_path=rel,
            folder=data.folder,
            message=(data.message or "").strip() or None,
            author_login=who,
            author_name=user.github_username or user.display_name or user.login,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Nun esiste.") from exc
    except github_user.GithubAuthRequired as exc:
        raise HTTPException(
            status_code=409,
            detail="GitHub ha negato l'operazione (serve accesso in scrittura, o ricollega).",
        ) from exc
    except github_user.GithubApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc) or "GitHub ha rifiutato.") from exc

    content_service.invalidate_github_cache(data.section)
    return DeleteOut(url=url)


def _frontend_redirect(settings, query: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"{settings.frontend_url}/?{query}", status_code=status.HTTP_302_FOUND
    )
