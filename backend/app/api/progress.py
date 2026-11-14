"""Progress stubs until Phase 3 XP rules land."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.schemas import ProgressOut
from app.config import get_settings

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("", response_model=ProgressOut)
def get_progress(request: Request) -> ProgressOut:
    settings = get_settings()
    # Stub: read preferred level from query later; for now defaults.
    level = 10
    return ProgressOut(
        xp_today=0,
        daily_goal=settings.daily_xp_goal,
        streak=0,
        level=level,
        tier=(level - 1) // 10 + 1,
    )
