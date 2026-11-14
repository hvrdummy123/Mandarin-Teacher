"""On-demand TTS replay endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_tts_returns_audio(client: TestClient) -> None:
    r = client.post("/api/tts", json={"text": "你好"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")
    assert r.content.startswith(b"ID3")
    assert "你好".encode() in r.content


def test_tts_rejects_empty(client: TestClient) -> None:
    r = client.post("/api/tts", json={"text": "   "})
    assert r.status_code == 400
