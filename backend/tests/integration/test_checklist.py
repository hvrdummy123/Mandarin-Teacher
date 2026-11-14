"""Automated versions of the Phase 1 hand checklist (FakeLLM)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.dictionary.memory import seed_basic_dictionary
from app.adapters.llm.fake import FakeLLM
from app.application.text_analyzer import TextAnalyzer


def test_restaurant_level5_reply(client: TestClient, fake_llm: FakeLLM) -> None:
    fake_llm.reply_text = "你好，请问几位？"
    fake_llm.reply_queue = ["你好，请问几位？"]
    r = client.post(
        "/api/sessions/open-topic",
        json={"topic_id": "restaurant", "level": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["session"]["topic_id"] == "restaurant"
    assert body["assistant_message"]["text"]
    sid = body["session"]["id"]
    fake_llm.reply_text = "好的，这是菜单。"
    turn = client.post(f"/api/sessions/{sid}/messages", json={"text": "我想吃面条"})
    assert turn.status_code == 200
    assert turn.json()["assistant_message"]["text"]


def test_hover_pinyin_yinhang_and_budui() -> None:
    a = TextAnalyzer(seed_basic_dictionary())
    bank = " ".join(t.pinyin for t in a.analyze("银行") if t.pinyin)
    budui = " ".join(t.pinyin for t in a.analyze("不对") if t.pinyin)
    assert "háng" in bank or "hang" in bank.lower()
    assert "xíng" not in bank
    assert "bú" in budui


def test_wrong_sentence_gets_correction(client: TestClient, fake_llm: FakeLLM) -> None:
    fake_llm.reply_text = "好的。"
    fake_llm.analysis = {
        "translation_en": "I yesterday go shop.",
        "reply_translation_en": "Okay.",
        "correction": {
            "better": "我昨天去商店买东西了。",
            "reason": "Remove the extra 了 and fix word order.",
        },
        "goal_progress": 0.1,
        "goal_done": False,
        "suggested_words": ["昨天"],
    }
    sid = client.post("/api/sessions", json={"mode": "free", "level": 10}).json()["id"]
    turn = client.post(
        f"/api/sessions/{sid}/messages",
        json={"text": "我昨天去了商店买东西了了"},
    )
    assert turn.status_code == 200
    corr = turn.json()["user_message"]["correction"]
    assert corr is not None
    assert "商店" in corr["better"]


def test_save_word_survives_list(client: TestClient) -> None:
    saved = client.post(
        "/api/words",
        json={
            "word": "银行",
            "pinyin": "yínháng",
            "definition": "bank",
            "hsk_level": 2,
            "context_sentence": "附近有银行吗？",
        },
    )
    assert saved.status_code == 200
    wid = saved.json()["id"]
    listed = client.get("/api/words").json()
    assert any(w["id"] == wid for w in listed)
    # "refresh"
    listed2 = client.get("/api/words").json()
    assert any(w["id"] == wid for w in listed2)


def test_level60_reply_differs_from_level5(client: TestClient, fake_llm: FakeLLM) -> None:
    fake_llm.reply_queue = ["你好！你叫什么名字？", "你好。最近工作顺利吗？有什么想聊的吗？"]
    s5 = client.post("/api/sessions", json={"mode": "free", "level": 5}).json()["id"]
    s60 = client.post("/api/sessions", json={"mode": "free", "level": 60}).json()["id"]
    r5 = client.post(f"/api/sessions/{s5}/messages", json={"text": "你好"}).json()
    r60 = client.post(f"/api/sessions/{s60}/messages", json={"text": "你好"}).json()
    assert r5["assistant_message"]["text"] != r60["assistant_message"]["text"]
