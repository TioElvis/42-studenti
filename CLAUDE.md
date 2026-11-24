# 42-Studenti — Project Rules

Web app for the **42 Roma** student community. UI is **100% Italian with Roman
slang (romanesco)**. Monorepo: FastAPI backend (`api/`), Next.js frontend
(`web/`), design references in `assets/`.

> Follows the global rules in `~/.claude/CLAUDE.md`. Local skills in
> `.claude/skills/`: fastapi-endpoint, alembic-migration, web-theme-component,
> vendor-42api-regen.

## Layout

```
api/            FastAPI + async SQLAlchemy + Alembic + vendored 42 client
  vendor/42api/ editable clone of github.com/Shadowaker/42api (intra42)
  app/          routers → services → models (+ schemas, intra.py adapter)
  alembic/      migrations     tests/  pytest suite
web/            Next.js 15 App Router + TS + Tailwind v4 + shadcn-style UI
  src/app/      routes: / (Bacheca), /eventi, /club
  src/components, src/lib, src/providers
assets/         classic/hacker/bento/bento-hacker .html, rome-pixel.png (design source)
```

## Commands

```bash
# Backend (api/, port 9000)
cd api && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ./vendor/42api
cp .env.example .env                    # fill in real values
alembic upgrade head
uvicorn app.main:app --reload --port 9000
pytest

# Frontend (web/, port 3000)
cd web && pnpm install
cp .env.example .env.local              # NEXT_PUBLIC_API_URL=http://localhost:9000
pnpm dev
pnpm build && pnpm lint && pnpm typecheck
```

Never hand-edit `api/vendor/42api/src/intra42/_sync/` (generated). Edit
`_async/` and run `python vendor/42api/scripts/unasync_generate.py`.

## Conventions

- **Layering:** `routers/` (HTTP) → `services/` (rules, ownership) → `models/`
  (ORM). `schemas/` are Pydantic DTOs. The 42 API is reached only via
  `app/intra.py`. Services never import FastAPI; domain errors live in
  `services/exceptions.py`.
- **No roles.** Every user is a flat student. Authorization is ownership-only,
  enforced server-side (IDOR-safe).
- **Auth.** 42 OAuth2 code flow in `routers/auth.py`. The 42 token is used once
  for `/me` and discarded; we issue our own HS256 JWT in an httpOnly cookie.
  The frontend gates on `GET /me` (cookie is on the API origin).
- **Secrets** only from env (`app/config.py`). Never hardcode; never commit `.env`.
- **Themes.** `classic`, `hacker`, `bento`, `bento-hacker` share layout and
  semantic CSS token *names*; only values swap under `[data-theme=...]` in
  `web/src/app/globals.css`. Palettes come from `assets/`.
- **Types.** TypeScript `strict` + `noUncheckedIndexedAccess`; Python type hints.

## Roadmap status

- Step 1 La Bacheca: DONE. Step 2 Eventi (official 42 Roma events, cached): DONE.
- Step 3 Club: "Prossimamente" view only (no backend CRUD).
- **TODO Step 2.1 — do NOT implement yet:** students propose community events.
  Markers: `POST /events` note in `api/app/routers/events.py` and
  `api/app/intra.py`; "Proponi un evento" TODO in
  `web/src/components/eventi/events-grid.tsx`. Keep proposed events clearly
  separate from official 42 events.
