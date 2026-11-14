"""Debug endpoints — timings for voice turns."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/timings")
def timings(request: Request) -> dict[str, Any]:
    state = request.app.state.container
    return {"turns": list(state.timings[-50:])}
