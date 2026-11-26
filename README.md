# 42 Studenti

The web app of the **42 Roma** student community: *code, peer learning and a beer
after the push.* The UI defaults to Italian with Roman slang (*romanesco*) and can
be switched to English. Login is **42 OAuth2**, open to 42 Roma students only.
There are no admin roles.

## Features

| Section | What it does |
|---------|--------------|
| **Bacheca** (board) | Posts with categories, search, likes, comments, polls and RSVPs, updated live over WebSocket |
| **Eventi** (events) | Upcoming official 42 Roma events, with sign-up and cancellation on the 42 Intra and the list of attendees |
| **Studenti** (students) | Student search, profiles, follows and leaderboards |
| **Club** | Coming soon |
| **Staff** | Contact form that opens a pre-filled email |
| **Materiale** / **Archivio** | Browse, preview and upload files stored in a private GitHub repository |

Students also get in-app notifications, with their own settings.

## Stack

| Part | Technology |
|------|------------|
| `api/` (port 9000) | Python 3.11+, FastAPI, async SQLAlchemy 2, Alembic, Pydantic 2, JWT in an httpOnly cookie, vendored 42 client (`intra42`) |
| `web/` (port 3000) | Next.js 15 (App Router), strict TypeScript, Tailwind CSS 4, shadcn-style UI |
| Database | PostgreSQL (e.g. Supabase, used as plain Postgres), SQLite in tests |

## Layout

```
api/              FastAPI backend
  app/            routers → services → models (+ schemas, intra*.py adapters)
  alembic/        database migrations
  tests/          pytest suite
  vendor/42api/   editable clone of github.com/Shadowaker/42api
web/              Next.js frontend
  src/            app/ (routes), components/, lib/, providers/
assets/           design references for the themes
```

## Prerequisites

- Python 3.11+
- Node.js 18.18+ and pnpm
- A PostgreSQL database
- A [42 OAuth application](https://profile.intra.42.fr/oauth/applications) with
  redirect URI `http://localhost:9000/auth/42/callback` and the scopes `public`
  and `profile`

## Backend setup

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./vendor/42api

cp .env.example .env          # fill in the values
alembic upgrade head          # create the tables
uvicorn app.main:app --reload --port 9000
```

The API runs on <http://localhost:9000>. Interactive docs are at `/docs`
(disabled in production), and `/health` reports whether the server is up.

### Environment variables (`api/.env`)

[`api/.env.example`](api/.env.example) documents every option. These are the main ones:

| Variable | Description |
|----------|-------------|
| `FORTY_TWO_UID`, `FORTY_TWO_SECRET` | Credentials of your 42 application |
| `FORTY_TWO_CALLBACK_URL` | Must match the redirect URI registered on 42 exactly |
| `FORTY_TWO_CAMPUS_ID` | Campus allowed to log in and source of the events (42 Roma: `30`) |
| `JWT_SECRET` | Long random string: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `TOKEN_ENCRYPTION_KEY` | Fernet key that encrypts stored 42 tokens; derived from `JWT_SECRET` if empty |
| `DATABASE_URL` | Runtime connection, `postgresql+asyncpg://…` (pooled, port 6543 on Supabase) |
| `DIRECT_URL` | Direct connection used by Alembic (port 5432) |
| `FRONTEND_URL` | Frontend origin, used for CORS and redirects |
| `GITHUB_REPO`, `GITHUB_BRANCH` | Repository and branch holding Materiale and Archivio |
| `GITHUB_WRITE_TOKEN` | Server token that reads and commits to the private repository |
| `GITHUB_SPECIAL_USERS` | Comma-separated 42 logins allowed to upload to Archivio and delete files |

> Do not add `?pgbouncer=true` to the database URL. The app detects the Supabase
> pooler by itself.

In production (`ENV=production`) the app refuses to start without the required
secrets or with `COOKIE_SECURE` off.

## Frontend setup

```bash
cd web
pnpm install
cp .env.example .env.local
pnpm dev                      # http://localhost:3000
```

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL. Leave blank to use port 9000 on the same host (useful on a LAN) |
| `NEXT_PUBLIC_STAFF_EMAIL` | Recipient of the Staff contact form |

## Tests and checks

```bash
# in api/, with the virtualenv active
pytest

# in web/
pnpm lint
pnpm typecheck
pnpm build
```

## How it works

### Login

1. The frontend shows the login window until `GET /me` succeeds.
2. `GET /auth/42` sends the student to the 42 authorization page.
3. The callback checks the `state` value, exchanges the code, reads the 42
   profile and rejects accounts from other campuses.
4. The backend saves the user and sets its own session JWT in an httpOnly cookie.
   42 tokens never reach the browser; they are stored encrypted so the app can
   sign students up to events.

If the API is asleep (free hosting), the frontend shows a wake-up screen and
retries until the server answers.

### Materiale and Archivio

Their content lives in a separate **private** repository and is never copied into
this one. The API lists it through GitHub and passes file contents through memory.
Uploads are direct commits: Materiale is open to logged-in students, while
Archivio uploads and all deletions are limited to `GITHUB_SPECIAL_USERS`.

### Themes

`classic`, `hacker`, `classic-modern` and `hacker-modern` share the same layout and
CSS token names; only the values change, in `web/src/app/globals.css`. The theme
and language are chosen in the settings window.

## Development notes

- Backend layering is `routers` → `services` → `models`. Services don't import
  FastAPI, and authorization is based on ownership, enforced on the server.
- Never edit `api/vendor/42api/src/intra42/_sync/` by hand. Edit `_async/`, then
  run `python vendor/42api/scripts/unasync_generate.py` from `api/`.
- Never commit `.env` files.

## Roadmap

- [x] Bacheca
- [x] Eventi (official 42 Roma events)
- [ ] Events proposed by students
- [ ] Clubs (only the "coming soon" page exists)
