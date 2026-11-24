---
name: fastapi-endpoint
description: Use when adding or changing API routes, services, models or schemas in 42-studenti/api (FastAPI + async SQLAlchemy) - layering, ownership-only authorization, 42 calls via app/intra.py, domain errors and pytest patterns.
---

# FastAPI endpoint (42-studenti/api)

## Layering (dependencies point inward)
`routers/` (HTTP) -> `services/` (rules, ownership) -> `models/` (ORM).
`schemas/` are Pydantic v2 DTOs. Services never import FastAPI. Domain errors
are defined in `app/services/exceptions.py`; routers translate them to HTTP.

## Adding a feature, in order
1. **Model** in `app/models/<name>.py`; export it in `models/__init__.py`.
   Schema change? Run the `alembic-migration` skill.
2. **Schema** in `app/schemas/<name>.py` (separate Create/Update/Read DTOs;
   never return ORM objects or secrets directly).
3. **Service** in `app/services/<name>.py`: async functions taking an
   `AsyncSession` and the acting user. Raise domain exceptions, no HTTP.
4. **Router** in `app/routers/<name>.py`, registered in `app/main.py`. Use the
   dependencies in `app/deps.py` (db session, current user).
5. **Test** in `api/tests/test_<name>.py`.

## Rules
- **No roles.** Every user is a flat student. Authorization is
  ownership-based and checked in the service layer (IDOR-safe): an
  edit/delete must verify `resource.author_id == user.id`.
  Return 404 (not 403) for foreign private resources when existence is secret.
- All 42 API access goes through `app/intra.py`. Never call `intra42` from
  routers or services directly.
- Secrets and settings only via `app/config.py` (env). Never hardcode.
- Use `app/ratelimit.py` on write or expensive endpoints.
- Validate and bound inputs in schemas (`max_length`, `ge/le`, enums from
  `models/enums.py`). Always use SQLAlchemy expressions, no raw string SQL.
- Auth is our own HS256 JWT in an httpOnly cookie (`app/security.py`),
  derived from the 42 OAuth flow in `routers/auth.py`.
- Realtime notifications go through `app/realtime.py` and `routers/ws.py`.

## Tests
- `api/pytest.ini`: `asyncio_mode=auto`, `testpaths=tests`.
- `tests/conftest.py` sets env, uses in-memory SQLite and seeds users, and
  provides an ASGI `AsyncClient`. Reuse its fixtures; set env vars before
  importing `app`.
- Cover: happy path, 401 unauthenticated, 403/404 for another user's
  resource, validation error (422).

## Verify
```bash
cd api && source .venv/bin/activate
pytest tests/test_<name>.py && pytest
```
