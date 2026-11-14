"""Liveness and readiness probes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.adapters.persistence.db import check_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> JSONResponse:
    state = request.app.state.container
    state.refresh_readiness_flags()
    settings = state.settings

    checks: dict[str, bool] = {
        "database": check_db(state.engine),
        "dictionary": settings.dictionary_loaded,
        "whisper": settings.whisper_loaded,
        "llm": len(settings.configured_llm_providers()) > 0,
    }
    ready = all(checks.values())
    body: dict[str, Any] = {"ready": ready, "checks": checks}
    return JSONResponse(content=body, status_code=200 if ready else 503)
