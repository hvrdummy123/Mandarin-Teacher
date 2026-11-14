"""Shared fixtures for Phase 0+."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from app.adapters.dictionary.memory import seed_basic_dictionary
from app.adapters.llm.fake import FakeLLM
from app.adapters.llm.fallback import FallbackChain
from app.adapters.persistence.db import create_db_engine, make_session_factory
from app.config import Settings, get_settings
from app.container import AppState, build_chat_services
from app.main import create_app


class FakeTTS:
    name = "fake-tts"

    async def synthesize(self, text: str, *, rate: str = "+0%") -> bytes:
        return b"ID3" + text.encode("utf-8")

    async def stream_sentences(self, text: str, *, rate: str = "+0%"):
        data = await self.synthesize(text, rate=rate)
        if data:
            yield data


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def run_migrations(database_url: str) -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.attributes["connection_url"] = database_url
    command.upgrade(cfg, "head")


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    get_settings.cache_clear()
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'duihua.db'}",
        dictionary_db_path=tmp_path / "dictionary.db",
        data_dir=tmp_path,
        tts_cache_dir=tmp_path / "tts",
        gemini_api_key="",
        openrouter_api_key="",
        llm_providers="gemini,openrouter",
        whisper_loaded=False,
        dictionary_loaded=False,
    )


@pytest.fixture
def migrated_engine(tmp_settings: Settings) -> Generator[Engine, None, None]:
    run_migrations(tmp_settings.database_url)
    engine = create_db_engine(tmp_settings)
    yield engine
    engine.dispose()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def app_state(tmp_settings: Settings, migrated_engine: Engine, fake_llm: FakeLLM) -> AppState:
    dictionary = seed_basic_dictionary()
    llm = FallbackChain(providers=[fake_llm])
    state = AppState(
        settings=tmp_settings,
        engine=migrated_engine,
        session_factory=make_session_factory(migrated_engine),
        dictionary=dictionary,
        llm=llm,
        chat_services=build_chat_services(tmp_settings, dictionary, llm),
        stt=None,
        tts=FakeTTS(),
    )
    # Pretend dictionary file exists for readiness probes that check the path.
    Path(tmp_settings.dictionary_db_path).write_bytes(b"x")
    state.refresh_readiness_flags()
    return state


@pytest.fixture
def client(app_state: AppState) -> Generator[TestClient, None, None]:
    application = create_app(container=app_state)
    with TestClient(application) as test_client:
        yield test_client
