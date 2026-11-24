"""Application settings, loaded once from the environment (12-factor).

Every secret and environment-specific value is read here and nowhere else, so
the rest of the code depends on a typed ``Settings`` object rather than on
``os.environ``. Nothing in this module has a hardcoded secret default.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root ``assets/`` dir (…/42-studenti/assets): holds the file-based
# Materiale / Archivio content served by the content router.
_DEFAULT_ASSETS_DIR = str(Path(__file__).resolve().parents[2] / "assets")

# A browser-like User-Agent for every outbound call to 42: api.intra.42.fr is
# behind Cloudflare, which serves a 403 bot challenge to the default
# ``python-httpx`` UA from datacenter IPs (so OAuth fails once deployed).
FORTY_TWO_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    env: str = Field(default="development", alias="ENV")
    port: int = Field(default=9000, alias="PORT")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    # --- 42 OAuth2 (Authorization Code flow, scope "public") ---
    forty_two_uid: str = Field(default="", alias="FORTY_TWO_UID")
    forty_two_secret: str = Field(default="", alias="FORTY_TWO_SECRET")
    forty_two_callback_url: str = Field(
        default="http://localhost:9000/auth/42/callback",
        alias="FORTY_TWO_CALLBACK_URL",
    )
    # 42 Roma campus id on the Intra (used for the public events feed).
    forty_two_campus_id: int = Field(default=30, alias="FORTY_TWO_CAMPUS_ID")
    # OAuth scopes requested at login. "profile" is needed to register the user
    # to events on their behalf (POST /v2/events_users); "public" covers /me.
    oauth_scope: str = Field(default="public profile", alias="OAUTH_SCOPE")

    # --- Our own session JWT (NOT the 42 token) ---
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60 * 24 * 7, alias="JWT_EXPIRE_MINUTES")

    # Key used to encrypt the stored 42 user tokens at rest (Fernet, urlsafe
    # base64 of 32 bytes). If empty, a key is derived from JWT_SECRET.
    token_encryption_key: str = Field(default="", alias="TOKEN_ENCRYPTION_KEY")

    # --- Cookies ---
    cookie_name: str = Field(default="access_token", alias="COOKIE_NAME")
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    cookie_samesite: str = Field(default="lax", alias="COOKIE_SAMESITE")
    cookie_domain: str | None = Field(default=None, alias="COOKIE_DOMAIN")

    # --- Database ---
    # Runtime (async, asyncpg). Alembic uses DIRECT_URL (see alembic/env.py).
    database_url: str = Field(default="", alias="DATABASE_URL")
    direct_url: str = Field(default="", alias="DIRECT_URL")

    # --- Events cache TTL (seconds) to stay well under 42 API rate limits ---
    events_cache_ttl: int = Field(default=300, alias="EVENTS_CACHE_TTL")

    # --- File-based content (Materiale / Archivio) served from assets/ ---
    assets_dir: str = Field(default=_DEFAULT_ASSETS_DIR, alias="ASSETS_DIR")
    # Client/proxy cache lifetime (seconds) for cacheable GET responses.
    http_cache_seconds: int = Field(default=60, alias="HTTP_CACHE_SECONDS")

    # --- Optional: serve Materiale/Archivio live from a GitHub repo ---
    # When GITHUB_REPO is set (e.g. "TioElvis/42-studenti"), content is read
    # from that repo's assets/ via the GitHub API (public repo = no token
    # needed); otherwise it falls back to the local assets_dir.
    github_repo: str = Field(default="", alias="GITHUB_REPO")
    github_branch: str = Field(default="main", alias="GITHUB_BRANCH")
    github_cache_ttl: int = Field(default=300, alias="GITHUB_CACHE_TTL")
    # Server-side token (classic PAT with `repo`, or fine-grained Contents RW on
    # the repo). When set, the backend reads a PRIVATE repo and commits
    # contributions on students' behalf — no per-student link / collaborator.
    github_write_token: str = Field(default="", alias="GITHUB_WRITE_TOKEN")

    @field_validator("github_repo")
    @classmethod
    def _normalize_github_repo(cls, v: str) -> str:
        """Accept either ``owner/name`` or a full GitHub URL; store ``owner/name``."""
        v = v.strip()
        if not v:
            return v
        for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
            if v.startswith(prefix):
                v = v[len(prefix):]
                break
        return v.rstrip("/").removesuffix(".git")

    # --- Optional: let students link their own GitHub to contribute to assets/ ---
    # A GitHub OAuth App (the feature is hidden until these are set).
    github_oauth_client_id: str = Field(default="", alias="GITHUB_OAUTH_CLIENT_ID")
    github_oauth_secret: str = Field(default="", alias="GITHUB_OAUTH_SECRET")
    github_oauth_callback_url: str = Field(
        default="http://localhost:9000/github/link/callback",
        alias="GITHUB_OAUTH_CALLBACK_URL",
    )
    # Comma-separated 42 logins allowed to contribute to the ARCHIVE section.
    # Empty = archive contributions are closed to everyone. Material is open to
    # any linked 42 Roma student.
    github_archive_allow: str = Field(default="", alias="GITHUB_ARCHIVE_ALLOW")

    @property
    def archive_allow(self) -> set[str]:
        return {x.strip().lower() for x in self.github_archive_allow.split(",") if x.strip()}

    def can_contribute_archive(self, login: str) -> bool:
        return login.lower() in self.archive_allow

    @property
    def github_oauth_configured(self) -> bool:
        return bool(self.github_oauth_client_id and self.github_oauth_secret)

    @property
    def github_server_writes(self) -> bool:
        """Server-token mode: the backend does reads/writes with its own token."""
        return bool(self.github_repo) and bool(self.github_write_token)

    @property
    def github_contrib_configured(self) -> bool:
        # Contributions need an upstream repo, plus either the server token
        # (backend commits for everyone) or an OAuth app (per-student tokens).
        return bool(self.github_repo) and (
            bool(self.github_write_token) or self.github_oauth_configured
        )

    @field_validator("cookie_samesite")
    @classmethod
    def _valid_samesite(cls, v: str) -> str:
        v = v.lower()
        if v not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be one of: lax, strict, none")
        return v

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}

    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_url]

    def async_database_url(self) -> str:
        """Normalize the runtime URL to the asyncpg driver (asyncpg-safe)."""
        url, _ = asyncpg_url_and_connect_args(self.database_url)
        return url

    def async_connect_args(self) -> dict[str, Any]:
        """Driver connect args for the runtime engine (asyncpg)."""
        _, connect_args = asyncpg_url_and_connect_args(self.database_url)
        return connect_args


def _coerce_driver(url: str, target: str) -> str:
    """Rewrite the scheme of a Postgres URL to a specific SQLAlchemy driver.

    Leaves non-postgres URLs (e.g. sqlite for tests) untouched.
    """
    if not url or url.startswith("sqlite"):
        return url
    for prefix in ("postgresql+asyncpg", "postgresql+psycopg", "postgresql", "postgres"):
        if url.startswith(prefix + "://"):
            return target + url[len(prefix):]
    return url


# Query params that libpq/Prisma-style URLs carry but asyncpg's connect() rejects.
# (asyncpg uses ``ssl=`` instead of ``sslmode=`` and has no concept of ``pgbouncer``.)
_ASYNCPG_DROP_PARAMS = {
    "pgbouncer",
    "sslmode",
    "channel_binding",
    "connect_timeout",
    "options",
    "target_session_attrs",
}


def asyncpg_url_and_connect_args(raw: str) -> tuple[str, dict[str, Any]]:
    """Return an asyncpg-safe URL plus connect args for a Postgres/SQLite URL.

    - Coerces the driver to ``postgresql+asyncpg`` (SQLite is left untouched).
    - Strips query params asyncpg can't accept (notably ``pgbouncer=true`` as
      used by Supabase's pooler) so they don't reach ``asyncpg.connect()``.
    - Translates ``sslmode`` to asyncpg's ``ssl`` connect arg.
    - For the Supabase transaction pooler (port 6543 / ``pgbouncer=true`` /
      host containing ``pooler``), disables prepared-statement caching, which
      is incompatible with pgbouncer in transaction mode.
    """
    if not raw or raw.startswith("sqlite"):
        return raw, {}

    url = _coerce_driver(raw, "postgresql+asyncpg")
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)

    connect_args: dict[str, Any] = {}
    pooled = (parts.port == 6543) or ("pooler" in (parts.hostname or ""))
    kept: list[tuple[str, str]] = []
    for key, value in pairs:
        lowered = key.lower()
        if lowered == "pgbouncer" and value.lower() == "true":
            pooled = True
            continue
        if lowered == "sslmode":
            if value.lower() not in {"disable", "allow"}:
                connect_args["ssl"] = True
            continue
        if lowered in _ASYNCPG_DROP_PARAMS:
            continue
        kept.append((key, value))

    if pooled:
        # pgbouncer (transaction mode) can't keep server-side prepared statements.
        connect_args["statement_cache_size"] = 0

    clean = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))
    return clean, connect_args


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
