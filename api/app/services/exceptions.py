"""Framework-free domain errors.

Routers translate these into HTTP responses; the service layer never imports
FastAPI, so the rules stay transport-agnostic.
"""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for domain-level failures."""


class NotFoundError(ServiceError):
    """The requested resource does not exist."""


class ForbiddenError(ServiceError):
    """The caller is authenticated but does not own the resource."""


class ConflictError(ServiceError):
    """The action conflicts with the current state (e.g. the sondaggio is full)."""
