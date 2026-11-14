"""Health and readiness probes."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.container import AppState
from app.main import create_app


def test_healthz_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_not_ready_when_assets_missing(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    assert body["checks"]["database"] is True
    # Fixture may plant a placeholder dictionary file; whisper/llm still block readiness.
    assert body["checks"]["whisper"] is False
    assert body["checks"]["llm"] is False
    assert body["ready"] is False


def test_readyz_ready_when_all_checks_pass(app_state: AppState) -> None:
    dict_path = Path(app_state.settings.dictionary_db_path)
    dict_path.write_bytes(b"sqlite-placeholder")
    app_state.settings.dictionary_loaded = True
    app_state.settings.whisper_loaded = True
    app_state.settings.gemini_api_key = "test-key"

    with TestClient(create_app(container=app_state)) as client:
        response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert all(body["checks"].values())


def test_timings_empty(client: TestClient) -> None:
    response = client.get("/api/debug/timings")
    assert response.status_code == 200
    assert response.json() == {"turns": []}
