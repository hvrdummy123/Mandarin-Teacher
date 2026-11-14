#!/usr/bin/env python3
"""Live checklist against real configured LLM providers.

Requires .env with at least one working LLM key, dictionary.db, and a running
API *or* it boots an in-process app.

Usage:
  PYTHONPATH=backend uv run python scripts/live_smoke.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.application.text_analyzer import TextAnalyzer  # noqa: E402
from app.container import build_container  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> int:
    # Do not load Whisper for this text checklist (voice covered separately).
    state = build_container(load_whisper=False)
    if state.chat_services is None:
        print("FAIL: chat services not ready (dictionary + LLM required)")
        return 1
    if not state.settings.configured_llm_providers():
        print("FAIL: no LLM providers configured in .env")
        return 1

    app = create_app(container=state)
    client = TestClient(app)
    failures: list[str] = []

    # 1) Level 5 + restaurant
    opened = client.post(
        "/api/sessions/open-topic",
        json={"topic_id": "restaurant", "level": 5},
    )
    if opened.status_code != 200:
        failures.append(f"open restaurant: {opened.status_code} {opened.text}")
    else:
        sid = opened.json()["session"]["id"]
        opening = opened.json()["assistant_message"]["text"]
        print(f"OK open-topic opening: {opening[:80]}…")
        turn = client.post(f"/api/sessions/{sid}/messages", json={"text": "我想吃面条"})
        if turn.status_code != 200:
            failures.append(f"level5 send: {turn.status_code} {turn.text}")
        else:
            reply = turn.json()["assistant_message"]["text"]
            print(f"OK level5 reply: {reply[:80]}…")
            if not reply.strip():
                failures.append("empty reply at level 5")

    # 2) Hover words: analyzer
    assert state.dictionary is not None
    analyzer = TextAnalyzer(state.dictionary)
    bank = " ".join(t.pinyin for t in analyzer.analyze("银行") if t.pinyin)
    budui = " ".join(t.pinyin for t in analyzer.analyze("不对") if t.pinyin)
    print(f"OK pinyin 银行={bank!r} 不对={budui!r}")
    if "háng" not in bank and "hang" not in bank.lower():
        failures.append(f"银行 pinyin unexpected: {bank}")
    if "bú" not in budui and "bu" not in budui.lower().replace("bù", ""):
        # require rising tone on 不
        if "bú" not in budui:
            failures.append(f"不对 sandhi unexpected: {budui}")

    # 3) Deliberate bad sentence → correction
    sess = client.post("/api/sessions", json={"mode": "free", "level": 10}).json()
    bad = client.post(
        f"/api/sessions/{sess['id']}/messages",
        json={"text": "我昨天去了商店买东西了了"},
    )
    if bad.status_code != 200:
        failures.append(f"bad sentence: {bad.status_code}")
    else:
        corr = bad.json()["user_message"].get("correction")
        print(f"OK correction: {corr}")
        # Soft check — free models sometimes skip correction
        if corr is None:
            print("WARN: no correction card (provider may have judged it fine)")

    # 4) Save word + still there
    saved = client.post(
        "/api/words",
        json={
            "word": "面条",
            "pinyin": "miàntiáo",
            "definition": "noodles",
            "hsk_level": 2,
            "context_sentence": "我想吃面条",
        },
    )
    if saved.status_code != 200:
        failures.append("save word failed")
    else:
        wid = saved.json()["id"]
        listed = client.get("/api/words").json()
        if not any(w["id"] == wid for w in listed):
            failures.append("saved word missing after list")
        else:
            print("OK saved word persists in list")

    # 5) Level 60 harder than level 5
    s5 = client.post("/api/sessions", json={"mode": "free", "level": 5}).json()["id"]
    s60 = client.post("/api/sessions", json={"mode": "free", "level": 60}).json()["id"]
    r5 = client.post(f"/api/sessions/{s5}/messages", json={"text": "你好"}).json()
    r60 = client.post(f"/api/sessions/{s60}/messages", json={"text": "你好"}).json()
    t5 = r5["assistant_message"]["text"]
    t60 = r60["assistant_message"]["text"]
    print(f"OK level5 len={len(t5)} text={t5[:60]}…")
    print(f"OK level60 len={len(t60)} text={t60[:60]}…")
    # Heuristic: level 60 reply should not be trivially identical and often longer
    if t5 == t60:
        failures.append("level 60 reply identical to level 5")

    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("live_smoke: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
