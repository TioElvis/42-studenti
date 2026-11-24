"""Token encryption key selection (valid key, invalid key, derived)."""

from __future__ import annotations

from cryptography.fernet import Fernet

from app.crypto import _build_fernet


def test_valid_key_is_used():
    key = Fernet.generate_key().decode()
    f = _build_fernet(key, "jwt-secret")
    assert f.decrypt(f.encrypt(b"hi")) == b"hi"


def test_invalid_key_falls_back_to_jwt():
    # A malformed TOKEN_ENCRYPTION_KEY must not crash — it derives from JWT.
    f = _build_fernet("this-is-not-a-valid-fernet-key", "jwt-secret")
    assert f.decrypt(f.encrypt(b"hi")) == b"hi"


def test_empty_key_derives_from_jwt():
    f = _build_fernet("", "jwt-secret")
    assert f.decrypt(f.encrypt(b"hi")) == b"hi"
    # Deterministic: same JWT secret → same key → cross-decryptable.
    other = _build_fernet("", "jwt-secret")
    assert other.decrypt(f.encrypt(b"hi")) == b"hi"
