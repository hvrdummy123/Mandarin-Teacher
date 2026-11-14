"""Alembic migrations reach head on a fresh database."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.config import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_fresh_db_reaches_head(tmp_path: Path) -> None:
    from tests.conftest import run_migrations

    db_path = tmp_path / "fresh.db"
    url = f"sqlite:///{db_path}"
    run_migrations(url)

    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    expected = {
        "alembic_version",
        "sessions",
        "messages",
        "corrections",
        "pronunciation_attempts",
        "saved_words",
        "xp_events",
        "daily_stats",
        "settings",
        "provider_usage",
    }
    assert expected.issubset(tables)

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == head
    engine.dispose()


def test_readyz_reflects_missing_dictionary(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.adapters.persistence.db import create_db_engine, make_session_factory
    from app.container import AppState
    from app.main import create_app
    from tests.conftest import run_migrations

    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        dictionary_db_path=tmp_path / "missing-dictionary.db",
        data_dir=tmp_path,
        tts_cache_dir=tmp_path / "tts",
        gemini_api_key="x",
        llm_providers="gemini",
        whisper_loaded=True,
    )
    run_migrations(settings.database_url)
    engine = create_db_engine(settings)
    state = AppState(settings=settings, engine=engine, session_factory=make_session_factory(engine))
    state.refresh_readiness_flags()
    assert state.settings.dictionary_loaded is False

    with TestClient(create_app(container=state)) as client:
        response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["checks"]["dictionary"] is False
    engine.dispose()
