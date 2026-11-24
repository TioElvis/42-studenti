---
name: vendor-42api-regen
description: Use when changing or debugging the vendored 42 client in 42-studenti/api/vendor/42api (intra42) - edit only the async source and regenerate the sync code with unasync.
---

# Vendored 42 client (`api/vendor/42api`)

Local editable clone of `github.com/Shadowaker/42api` (package `intra42`),
installed with `pip install -e ./vendor/42api`. The app reaches it only
through `app/intra.py`.

## Hard rule
`vendor/42api/src/intra42/_sync/` is **generated**. Never hand-edit it.
Edit `vendor/42api/src/intra42/_async/` and regenerate.

## Steps
1. Make the change in `_async/`.
2. Regenerate:
   ```bash
   cd api && source .venv/bin/activate
   pip install unasync ruff        # first time only
   python vendor/42api/scripts/unasync_generate.py
   ```
3. Check `git diff vendor/42api/src/intra42/_sync/`: it should be the
   mechanical mirror of your `_async/` change and nothing else.
4. If the public interface changed, update the adapter in `app/intra.py` and
   its parsing tests (`tests/test_intra_parse.py`, `tests/test_events.py`).
5. Run the tests: `pytest`.

## Rules
- Keep the app's use of the client inside `app/intra.py`; routers and services
  never import `intra42`.
- The 42 OAuth token is used once to read `/me` and discarded; do not add
  token storage in the client.
- Credentials (`FORTY_TWO_UID`, `FORTY_TWO_SECRET`) come from env only.
- Respect the 42 API rate limits; keep results cached where the app already
  caches (events).

## Verify
- `pytest` passes (tests do not call the real 42 API).
- `git status` shows `_sync/` changes only after a regeneration run.
