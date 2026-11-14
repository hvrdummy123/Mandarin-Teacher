"""Deterministic LLM for tests and offline demos."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class FakeLLM:
    name: str = "fake"
    reply_text: str = "你好！今天怎么样？"
    analysis: dict[str, object] = field(
        default_factory=lambda: {
            "translation_en": "Hello",
            "reply_translation_en": "Hello! How are you today?",
            "correction": None,
            "goal_progress": 0.2,
            "goal_done": False,
            "suggested_words": ["今天", "怎么样"],
        }
    )
    # Scripted replies for level post-check tests (popped in order).
    reply_queue: list[str] = field(default_factory=list)
    fail_times: int = 0
    fail_with: type[BaseException] = TimeoutError
    calls: list[dict[str, object]] = field(default_factory=list)

    async def complete(self, *, system: str, user: str, json_mode: bool = False) -> str:
        self.calls.append({"system": system, "user": user, "json_mode": json_mode})
        if self.fail_times > 0:
            self.fail_times -= 1
            raise self.fail_with("fake failure")
        if json_mode:
            return json.dumps(self.analysis, ensure_ascii=False)
        if self.reply_queue:
            return self.reply_queue.pop(0)
        return self.reply_text

    async def stream(self, *, system: str, user: str) -> AsyncIterator[str]:
        text = await self.complete(system=system, user=user, json_mode=False)
        # Yield character-ish chunks so clients exercise streaming.
        for i in range(0, len(text), 2):
            yield text[i : i + 2]
