"""FastAPI application factory and cross-cutting middleware.

Wires presentation (routers) to the rest of the app and applies the security
posture required by the workspace standards: restrictive CORS, security
headers, a request-body size cap, generic error bodies with a correlation id,
and fail-fast validation of required secrets in production.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import Settings, get_settings
from .routers import (
    auth,
    comments,
    content,
    events,
    follows,
    me,
    notifications,
    posts,
    profile,
    students,
    ws,
)
from .services.exceptions import ConflictError, ForbiddenError, NotFoundError

logger = logging.getLogger("app")

MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MiB


def _validate_production_secrets(settings: Settings) -> None:
    if not settings.is_production:
        return
    missing = [
        name
        for name, value in {
            "JWT_SECRET": settings.jwt_secret,
            "FORTY_TWO_UID": settings.forty_two_uid,
            "FORTY_TWO_SECRET": settings.forty_two_secret,
            "DATABASE_URL": settings.database_url,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required settings in production: {', '.join(missing)}")

    # The session cookie must be TLS-only in production, or it can be sent over
    # plain HTTP and hijacked. (SameSite=None also requires Secure.)
    if not settings.cookie_secure:
        raise RuntimeError("COOKIE_SECURE must be true in production")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _validate_production_secrets(settings)
    if not settings.jwt_secret:
        logger.warning("JWT_SECRET is empty — set it in api/.env before issuing tokens.")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="42 Studenti API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def _limit_and_secure(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_BODY_BYTES:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": "Richiesta troppo grande."},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Content-Length non valido."},
                )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # The content file endpoint streams assets the web app embeds (inline
        # PDFs in an <iframe>); it sets its own scoped frame-ancestors CSP, so we
        # skip the blanket X-Frame-Options: DENY only for it. Everything else
        # stays un-framable. (setdefault leaves the endpoint's own CSP intact.)
        path = request.url.path
        is_content_file = path.startswith("/content/") and path.endswith("/file")
        if not is_content_file:
            response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response

    _register_error_handlers(app)

    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(posts.router)
    app.include_router(comments.router)
    app.include_router(events.router)
    app.include_router(content.router)
    app.include_router(profile.router)
    app.include_router(students.router)
    app.include_router(follows.router)
    app.include_router(notifications.router)
    app.include_router(ws.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "42-studenti-api", "version": __version__}

    return app


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc) or "Non trovato."})

    @app.exception_handler(ForbiddenError)
    async def _forbidden(request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc) or "Nun te po' permette: è roba d'altri."},
        )

    @app.exception_handler(ConflictError)
    async def _conflict(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc) or "Nun se po' fà: c'è 'n conflitto."},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Keep only JSON-safe fields; drop ``ctx`` (may hold exception objects).
        errors = [
            {"loc": [str(p) for p in e.get("loc", [])], "msg": e.get("msg"), "type": e.get("type")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"detail": "Dati non validi.", "errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = uuid.uuid4().hex
        # Log the detail server-side only; never leak internals to the client.
        logger.exception("Unhandled error [%s]", correlation_id)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Ao, 'nte impanicà! Qualcosa è andato storto.",
                "correlation_id": correlation_id,
            },
        )


app = create_app()
