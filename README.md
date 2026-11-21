# 42 Roma Studenti

Il portale della community studentesca di **42 Roma** — *codice, peer learning e
'na birra dopo er push.* UI in italiano con slang romanesco, due temi 90s
intercambiabili (**Classico Romano** e **SPQR Hacker**), login con **42 OAuth2**.

- **La Bacheca** — feed sociale con post, categorie, like (`♥ Daje!`) e commenti.
- **Eventi** — eventi ufficiali di 42 Roma presi dall'Intra 42.
- **Club** — *Prossimamente*.

## Stack

| Parte | Tech |
|-------|------|
| `api/` (porta 9000) | Python 3.11+, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, JWT (httpOnly cookie), client 42 locale `intra42` |
| `web/` (porta 3000) | Next.js (App Router, TypeScript), Tailwind CSS v4, UI stile shadcn/ui, due temi via `[data-theme]` |
| Database | PostgreSQL (Supabase — solo Postgres, **niente** Supabase Auth/RLS) |

## Prerequisiti

- Python 3.11+ · Node 18+ · pnpm · un database PostgreSQL (es. Supabase)
- Una **42 OAuth application** (https://profile.intra.42.fr/oauth/applications)
  con redirect URI `http://localhost:9000/auth/42/callback` e scope `public`.

## 1) Backend (`api/`)

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e ./vendor/42api             # client 42 locale, in editable mode

cp .env.example .env                       # compila i valori reali (vedi sotto)
alembic upgrade head                       # crea le tabelle
uvicorn app.main:app --reload --port 9000
```

API su http://localhost:9000 — documentazione interattiva su `/docs` (solo in dev).

### Variabili d'ambiente (`api/.env`)

| Variabile | Descrizione |
|-----------|-------------|
| `FORTY_TWO_UID` / `FORTY_TWO_SECRET` | credenziali della tua app 42 |
| `FORTY_TWO_CALLBACK_URL` | deve combaciare **esattamente** col redirect registrato su 42 |
| `FORTY_TWO_CAMPUS_ID` | id campus 42 Roma sull'Intra (default `61`) |
| `JWT_SECRET` | stringa random lunga: `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | Postgres async (asyncpg), es. `postgresql+asyncpg://user:pass@host:6543/postgres?pgbouncer=true` |
| `DIRECT_URL` | connessione diretta (5432) usata da Alembic per le migrazioni |
| `FRONTEND_URL` | origine del frontend per CORS/redirect (default `http://localhost:3000`) |

> **Supabase:** usa solo il Postgres. `DATABASE_URL` = connessione *pooled*
> (pgbouncer, 6543); `DIRECT_URL` = connessione *diretta* (5432) per le migrazioni.

### Il client 42 (`api/vendor/42api`)

È un clone **editable** di [`Shadowaker/42api`](https://github.com/Shadowaker/42api)
(il pacchetto `intra42`). Gli eventi del campus sono letti tramite il metodo
`client.events.for_campus(campus_id)` che abbiamo aggiunto preservando lo stile
del progetto. `_sync/` è generato: modifica `_async/` e rigenera con
`python vendor/42api/scripts/unasync_generate.py`.

### Test

```bash
cd api && pytest            # suite dell'app
pytest vendor/42api/tests/unit   # test del client 42
```

## 2) Frontend (`web/`)

```bash
cd web
pnpm install
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:9000
pnpm dev                        # http://localhost:3000
```

Build di produzione: `pnpm build && pnpm start`. Qualità: `pnpm lint`, `pnpm typecheck`.

## Come funziona il login

1. Il frontend mostra la finestra **ACCEDI_AL_CAMPUS.EXE** finché `GET /me` dà 401.
2. **Accedi con 42** → `GET /auth/42` → pagina di autorizzazione 42 (scope `public`).
3. 42 reindirizza a `/auth/42/callback`: il backend valida lo `state` (CSRF),
   scambia il `code`, legge `/me`, fa l'upsert dell'utente e imposta un cookie di
   sessione **httpOnly** (il token 42 non raggiunge mai il browser).
4. Il frontend ricarica, `GET /me` riesce e si sbloccano **Bacheca**, **Eventi**, **Club**.

## Temi

Due temi 90s con **la stessa identica struttura**: cambiano solo le variabili CSS
(`[data-theme="classic"]` vs `[data-theme="hacker"]` in `web/src/app/globals.css`).
Si cambia dal pulsante **Impostazioni** (anche dalla schermata di login); la scelta
è salvata in `localStorage`.

## Roadmap

- [x] **Step 1 — La Bacheca** (post, categorie, like, commenti, controlli autore)
- [x] **Step 2 — Eventi** (feed ufficiale 42 Roma via `intra42`, con cache)
- [ ] **Step 2.1 — Proposta eventi dagli studenti** (TODO già marcati nel codice)
- [x] **Step 3 — Club** (vista "Prossimamente")

## Sicurezza

Auth ownership-based (niente ruoli), JWT con algoritmo fissato, cookie
`HttpOnly`/`SameSite`, CORS con allow-list, header di sicurezza, rate limit sugli
endpoint di auth, validazione input via Pydantic, errori generici con
correlation id. Dettagli nelle regole di workspace (`~/Projects/CLAUDE.md`).
