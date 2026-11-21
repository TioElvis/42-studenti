"""Hardening: production cookie safety + download header injection."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.main import _validate_production_secrets
from app.routers.content import _content_disposition


def _prod(**override):
    base = dict(
        is_production=True,
        jwt_secret="x",
        forty_two_uid="x",
        forty_two_secret="x",
        database_url="postgresql://x",
        cookie_secure=True,
    )
    base.update(override)
    return SimpleNamespace(**base)


def test_production_requires_secure_cookie():
    _validate_production_secrets(_prod())  # fully configured → ok
    with pytest.raises(RuntimeError):
        _validate_production_secrets(_prod(cookie_secure=False))
    with pytest.raises(RuntimeError):
        _validate_production_secrets(_prod(jwt_secret=""))


def test_non_production_skips_checks():
    # Insecure cookie is allowed outside production (local dev over HTTP).
    _validate_production_secrets(_prod(is_production=False, cookie_secure=False))


def test_content_disposition_strips_injection():
    value = _content_disposition("attachment", 'ev"il\r\nX-Evil: 1.md')
    assert "\r" not in value and "\n" not in value
    assert value.startswith('attachment; filename="')
    # the quoted ASCII filename carries no raw quote that could end it early
    ascii_part = value.split('filename="', 1)[1].split('"', 1)[0]
    assert '"' not in ascii_part and "\\" not in ascii_part
