"""Full REST chat flow with FakeLLM."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.llm.fake import FakeLLM


def test_create_session_send_text_save_word(client: TestClient, fake_llm: FakeLLM) -> None:
    fake_llm.reply_text = "你好！今天喝咖啡吗？"
    fake_llm.analysis = {
        "translation_en": "I want coffee",
        "reply_translation_en": "Hello! Do you want coffee today?",
        "correction": {"better": "我想喝咖啡。", "reason": "Add 想 for want."},
        "goal_progress": 0.4,
        "goal_done": False,
        "suggested_words": ["咖啡", "喝"],
    }

    topics = client.get("/api/topics")
    assert topics.status_code == 200
    assert len(topics.json()) == 30

    session = client.post(
        "/api/sessions",
        json={"mode": "topic", "topic_id": "cafe", "level": 8},
    )
    assert session.status_code == 200
    sid = session.json()["id"]

    turn = client.post(f"/api/sessions/{sid}/messages", json={"text": "我要咖啡"})
    assert turn.status_code == 200
    body = turn.json()
    assert body["assistant_message"]["text"]
    assert body["assistant_message"]["tokens"]
    assert body["user_message"]["correction"]["better"] == "我想喝咖啡。"
    assert body["analysis"]["translation_en"] == "I want coffee"

    saved = client.post(
        "/api/words",
        json={
            "word": "咖啡",
            "pinyin": "kāfēi",
            "definition": "coffee",
            "hsk_level": 2,
            "context_sentence": body["assistant_message"]["text"],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["word"] == "咖啡"

    words = client.get("/api/words")
    assert any(w["word"] == "咖啡" for w in words.json())

    messages = client.get(f"/api/sessions/{sid}/messages")
    assert len(messages.json()) == 2


def test_level_endpoint(client: TestClient) -> None:
    r = client.get("/api/levels/30")
    assert r.status_code == 200
    assert r.json()["tier"] == 3
    assert r.json()["vocab_size"] > 150
