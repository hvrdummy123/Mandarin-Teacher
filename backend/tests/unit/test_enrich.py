"""Live speech enrich endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_enrich_returns_pinyin_and_gloss(client: TestClient) -> None:
    r = client.post("/api/enrich", json={"text": "你好，我是 Mary"})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "你好，我是 Mary"
    assert any(t["surface"] == "你好" for t in body["tokens"])
    # Spoken sandhi may yield ní hǎo rather than citation nǐ hǎo.
    assert "hǎo" in body["pinyin_line"] or "hao" in body["pinyin_line"].lower()
    assert "wǒ" in body["pinyin_line"] or "wo" in body["pinyin_line"].lower()
    assert body["translation_en"]
