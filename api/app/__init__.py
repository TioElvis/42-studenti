"""42-Studenti API — FastAPI backend for the 42 Roma student community.

Layering (dependencies point inward only):

    routers/   -> presentation (HTTP, cookies, status codes)
    services/  -> application logic (ownership rules, orchestration)
    models/    -> persistence (SQLAlchemy ORM)
    schemas/   -> transport contracts (Pydantic v2)

The 42 Intra integration lives behind ``app.intra`` (adapter over the vendored
``intra42`` client), so the rest of the app never imports it directly.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
