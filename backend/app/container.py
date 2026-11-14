"""Composition root — wire adapters here, nowhere else."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.persistence.db import create_db_engine, make_session_factory
from app.config import Settings, get_settings
from app.logging import get_logger

log = get_logger(__name__)


@dataclass
class AppState:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    # Last 50 voice-turn timing dicts; filled in later phases.
    timings: list[dict[str, object]] = field(default_factory=list)

    def refresh_readiness_flags(self) -> None:
        """Probe dictionary file and whisper model presence for /readyz."""
        dict_path = Path(self.settings.dictionary_db_path)
        self.settings.dictionary_loaded = dict_path.is_file() and dict_path.stat().st_size > 0
        # Whisper is loaded lazily in P2; for P0 we only check whether a cache dir exists
        # or the configured model name is known — actual load happens later.
        # Mark unloaded until the STT adapter reports ready.
        # Leave whisper_loaded as-is if something already set it.


def build_container(settings: Settings | None = None) -> AppState:
    settings = settings or get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.tts_cache_dir).mkdir(parents=True, exist_ok=True)

    engine = create_db_engine(settings)
    session_factory = make_session_factory(engine)
    state = AppState(settings=settings, engine=engine, session_factory=session_factory)
    state.refresh_readiness_flags()
    log.info(
        "container_ready",
        dictionary_loaded=settings.dictionary_loaded,
        whisper_loaded=settings.whisper_loaded,
        llm_providers=settings.configured_llm_providers(),
    )
    return state
