"""Symmetric encryption for third-party tokens stored at rest (Fernet).

We keep each student's 42 access/refresh token so we can act on 42 on their
behalf (event sign-up). Those are sensitive, so they are encrypted in the
database. The key comes from ``TOKEN_ENCRYPTION_KEY`` (a Fernet key); if that
is unset we derive one from ``JWT_SECRET`` so local dev works out of the box.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings

logger = logging.getLogger("app.crypto")


def _build_fernet(token_key: str, jwt_secret: str) -> Fernet:
    """A Fernet from ``TOKEN_ENCRYPTION_KEY`` if it's a valid key, else one
    derived from ``JWT_SECRET``. An invalid key is a config mistake that must
    not take login down — we warn and fall back instead of raising."""
    key = (token_key or "").strip()
    if key:
        try:
            return Fernet(key.encode())
        except (ValueError, TypeError):
            logger.warning(
                "TOKEN_ENCRYPTION_KEY is not a valid Fernet key "
                "(must be 44 url-safe base64 chars); deriving from JWT_SECRET instead."
            )
    # Derive a valid 32-byte urlsafe-base64 Fernet key from the JWT secret.
    digest = hashlib.sha256(jwt_secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    return _build_fernet(settings.token_encryption_key, settings.jwt_secret)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str | None:
    """Return the plaintext, or None if the value can't be decrypted."""
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError):
        return None
