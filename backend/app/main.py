"""FastAPI entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import debug, health, meta, progress, sessions, tts, words, ws
from app.config import get_settings
from app.container import AppState, build_container
from app.logging import get_logger, setup_logging

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.log_level)
    # Whisper load can take a while on first run; do it at startup so /readyz is honest.
    container = build_container(settings, load_whisper=True)
    app.state.container = container
    log.info("app_started", host=settings.host, port=settings.port)
    yield
    log.info("app_stopped")


def create_app(container: AppState | None = None) -> FastAPI:
    settings = container.settings if container is not None else get_settings()
    app = FastAPI(
        title="对话 duihua",
        lifespan=lifespan if container is None else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(debug.router)
    app.include_router(sessions.router)
    app.include_router(words.router)
    app.include_router(meta.router)
    app.include_router(progress.router)
    app.include_router(tts.router)
    app.include_router(ws.router)

    if container is not None:
        app.state.container = container

    return app


app = create_app()
