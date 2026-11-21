"""The authenticated student's own profile."""

from __future__ import annotations

from fastapi import APIRouter

from ..deps import CurrentUser
from ..schemas.user import UserMe

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserMe)
async def read_me(user: CurrentUser) -> UserMe:
    return UserMe.model_validate(user)
