---
name: alembic-migration
description: Use when changing SQLAlchemy models or the database schema in 42-studenti/api - creating, reviewing and applying Alembic migrations (Postgres on Supabase in prod, SQLite in tests).
---

# Alembic migration (42-studenti/api)

Migrations live in `api/alembic/versions/` (numbered, latest is
`0010_github_link.py`). Production is Postgres (Supabase); tests build the
schema on in-memory SQLite from the models, not from migrations.

## Steps
1. Edit the model in `app/models/` and make sure it is imported in
   `app/models/__init__.py` (autogenerate only sees imported models).
2. Generate:
   ```bash
   cd api && source .venv/bin/activate
   alembic revision --autogenerate -m "short description"
   ```
   Rename the file to the next number (`0011_<slug>.py`) to keep the style.
3. **Review the generated file by hand.** Autogenerate misses or mangles:
   enum changes, server defaults, renamed columns (shows as drop + add),
   check constraints, and indexes.
4. Write a real `downgrade()`.
5. Apply and test the round trip:
   ```bash
   alembic upgrade head
   alembic downgrade -1 && alembic upgrade head
   ```
6. Run `pytest` (the model change must work on SQLite too).

## Rules
- Never edit a migration that is already applied in a shared database; add a
  new one.
- New NOT NULL columns on existing tables need a `server_default` or a
  backfill step first.
- Postgres enums: use `op.execute("ALTER TYPE ... ADD VALUE ...")` outside a
  transaction block when adding values; keep SQLite compatibility in mind for
  anything the tests import.
- Add indexes for new foreign keys and frequent filters.
- Never put secrets or real data in a migration.
- Do not point `DATABASE_URL` at production while experimenting; use a local
  or throwaway database.

## Verify
- `alembic heads` shows a single head.
- `alembic upgrade head` and `alembic downgrade -1` both succeed.
- `pytest` passes.
