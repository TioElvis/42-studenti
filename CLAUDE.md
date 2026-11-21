# 42-Roma-Studenti — Project Rules

Web app for the **42 Roma** student community. UI is **100% Italian with Roman
slang (romanesco)**. Monorepo: a FastAPI backend (`api/`) and a Next.js
frontend (`web/`), plus design references in `assets/`.

> Inherits the workspace rules in `~/Projects/CLAUDE.md` (SOLID, security by
> design, continuous memory). This file adds project-specific commands and
> conventions and never weakens those standards.

## Layout

```
42-roma-studenti/
  api/            FastAPI + SQLAlchemy(async) + Alembic + the vendored 42 client
    vendor/42api/ Local editable clone of github.com/Shadowaker/42api (intra42)
    app/          routers → services → models (+ schemas, intra adapter)
    alembic/      migrations
    tests/        pytest suite
  web/            Next.js App Router + TypeScript + Tailwind v4 + shadcn-style UI
    src/app/      routes: / (Bacheca), /eventi, /club
    src/components, src/lib, src/providers
  assets/         classic.html, hacker.html, rome-pixel.png (design source of truth)
```

## Commands

### Backend (`api/`, port 9000)
```bash
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./vendor/42api          # editable local 42 client
cp .env.example .env                    # then fill in real values
alembic upgrade head                    # apply migrations
uvicorn app.main:app --reload --port 9000
pytest                                  # run the test suite
```

### 42 client (`api/vendor/42api`)
Do **not** hand-edit `src/intra42/_sync/` — it is generated. Edit the async
source under `src/intra42/_async/` and regenerate:
```bash
pip install unasync ruff
python vendor/42api/scripts/unasync_generate.py
```

### Frontend (`web/`, port 3000)
```bash
cd web
pnpm install
cp .env.example .env.local              # NEXT_PUBLIC_API_URL=http://localhost:9000
pnpm dev                                # http://localhost:3000
pnpm build && pnpm lint && pnpm typecheck
```

## Conventions

- **Backend layering (deps point inward):** `routers/` (HTTP) → `services/`
  (rules, ownership) → `models/` (ORM). `schemas/` are Pydantic DTOs. The 42
  integration is hidden behind `app/intra.py` (adapter over `intra42`). Services
  never import FastAPI; domain errors live in `services/exceptions.py`.
- **No roles.** Every user is a flat `User` (student). Authorization is strictly
  ownership-based and enforced server-side (IDOR-safe): a user may edit/delete
  only their own posts and comments.
- **Auth.** 42 OAuth2 Authorization-Code flow in `routers/auth.py`. The 42 token
  is used once to read `/me` and discarded; we issue our own HS256 JWT in an
  httpOnly cookie. The frontend gates on `GET /me` (client-side) because the
  cookie is on the API origin.
- **Secrets** come only from the environment (`app/config.py`). Never hardcode
  them; never commit `.env`. `.gitignore` already excludes it.
- **Themes.** Both 90s themes share the same layout and semantic CSS token
  *names*; only the values swap under `[data-theme="classic"|"hacker"]` in
  `web/src/app/globals.css`. Palettes are lifted verbatim from `assets/`.
- **Types.** TypeScript `strict` (+ `noUncheckedIndexedAccess`); Python type
  hints throughout.

## Roadmap status

- **Step 1 — La Bacheca:** DONE (posts/comments/likes CRUD, categories, detail
  thread, ownership controls).
- **Step 2 — Eventi:** DONE (official 42 Roma events via `intra42`, cached).
- **Step 3 — Club:** "Prossimamente" view only (no backend CRUD).

### TODO (Step 2.1) — do NOT implement yet
Let students **propose** community events from the frontend. Markers are already
in place: `POST /events` stub note in `api/app/routers/events.py` and
`api/app/intra.py`; a "Proponi un evento" TODO in
`web/src/components/eventi/events-grid.tsx`. When building it, keep proposed
community events clearly separated from official 42 events.
