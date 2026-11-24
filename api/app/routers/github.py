"""Link a student's GitHub account and contribute files to assets/ via PR.

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
from ..ratelimit import auth_rate_limiter
from ..schemas.github import ContributeIn, ContributeOut, GithubStatus
from ..services import content as content_service
from ..services.exceptions import NotFoundError

logger = logging.getLogger("app.github")

router = APIRouter(prefix="/github", tags=["github"])

_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_STATE_COOKIE = "github_state"
_MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5 MiB


@router.get("/status", response_model=GithubStatus)
async def status_(settings: SettingsDep, user: CurrentUser) -> GithubStatus:
    return GithubStatus(
        configured=settings.github_contrib_configured,
        server_mode=settings.github_server_writes,
        linked=bool(user.github_username),
        username=user.github_username,
        can_archive=settings.can_contribute_archive(user.login),
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

    if not content_service.section_allowed(data.section):
        raise HTTPException(status_code=404, detail="Sezione non valida.")
    # The archive section is restricted to an allow-list of 42 logins.
    if data.section == "archive" and not settings.can_contribute_archive(user.login):
        raise HTTPException(
            status_code=403, detail="Solo alcuni studenti possono contribuì all'archivio."
        )

    # In server-token mode the backend commits for everyone (no per-student link
    # needed); otherwise the student must have linked their own GitHub.
    server = settings.github_server_writes
    student_token = github_user.github_token_of(user)
    if not server and (not student_token or not user.github_username):
        raise HTTPException(status_code=409, detail="Collega prima il tuo account GitHub.")

    try:
        rel = content_service.confine_rel(data.path)  # never escapes assets/<section>/
    except NotFoundError as exc:
        raise HTTPException(status_code=400, detail="Percorso non valido.") from exc

    # Normalize the body to base64 and enforce the size cap.
    if data.encoding == "base64":
        try:
            raw = base64.b64decode(data.content, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Contenuto base64 non valido.") from exc
        content_b64 = data.content
    else:
        raw = data.content.encode("utf-8")
        content_b64 = base64.b64encode(raw).decode("ascii")
    if len(raw) > _MAX_CONTENT_BYTES:
        raise HTTPException(status_code=413, detail="File troppo grande (max 5 MiB).")

    who = user.github_username or user.login
    message = (data.message or "").strip() or f"Add {data.section}/{rel}"
    title = (data.title or "").strip() or message
    body = f"Contributo di @{who} via 42 Studenti."
    try:
        if server:
            url = await github_user.contribute_server(
                settings=settings,
                mode=data.mode,
                section=data.section,
                rel_path=rel,
                content_b64=content_b64,
                message=message,
                title=title,
                body=body,
                author_name=user.github_username or user.display_name or user.login,
                author_login=who,
            )
            if data.mode == "push":
                content_service.invalidate_github_cache(data.section)
        elif data.mode == "push":
            url = await github_user.contribute_direct_push(
                settings=settings,
                token=student_token,
                section=data.section,
                rel_path=rel,
                content_b64=content_b64,
                message=message,
            )
            # The branch changed → drop the cached listing so it shows at once.
            content_service.invalidate_github_cache(data.section)
        else:
            url = await github_user.contribute_via_pr(
                settings=settings,
                token=student_token,
                login=user.github_username,
                section=data.section,
                rel_path=rel,
                content_b64=content_b64,
                message=message,
                title=title,
                body=body,
            )
    except github_user.GithubAuthRequired as exc:
        raise HTTPException(
            status_code=409,
            detail="GitHub ha negato l'operazione (serve accesso in scrittura, o ricollega).",
        ) from exc
    except github_user.GithubApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc) or "GitHub ha rifiutato.") from exc

    return ContributeOut(pr_url=url)


def _frontend_redirect(settings, query: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"{settings.frontend_url}/?{query}", status_code=status.HTTP_302_FOUND
    )
