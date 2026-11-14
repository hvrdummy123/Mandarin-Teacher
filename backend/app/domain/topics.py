"""Topic catalogue loaded from data/topics.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import REPO_ROOT


@dataclass(frozen=True)
class Topic:
    id: str
    title_en: str
    title_zh: str
    ai_role: str
    scenario: str
    user_goal: str
    keywords: tuple[str, ...]
    min_level: int


def topics_path() -> Path:
    return REPO_ROOT / "backend" / "data" / "topics.json"


@lru_cache
def load_topics() -> tuple[Topic, ...]:
    raw = json.loads(topics_path().read_text(encoding="utf-8"))
    topics: list[Topic] = []
    for item in raw:
        topics.append(
            Topic(
                id=item["id"],
                title_en=item["title_en"],
                title_zh=item["title_zh"],
                ai_role=item["ai_role"],
                scenario=item["scenario"],
                user_goal=item["user_goal"],
                keywords=tuple(item.get("keywords") or []),
                min_level=int(item.get("min_level") or 1),
            )
        )
    return tuple(topics)


def get_topic(topic_id: str | None) -> Topic | None:
    if not topic_id:
        return None
    for t in load_topics():
        if t.id == topic_id:
            return t
    return None
