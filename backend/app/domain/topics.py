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
    opening_zh: str = ""
    opening_en: str = ""


def topics_path() -> Path:
    return REPO_ROOT / "backend" / "data" / "topics.json"


def openings_path() -> Path:
    return REPO_ROOT / "backend" / "data" / "topic_openings.json"


@lru_cache
def _load_openings() -> dict[str, dict[str, str]]:
    path = openings_path()
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


@lru_cache
def load_topics() -> tuple[Topic, ...]:
    raw = json.loads(topics_path().read_text(encoding="utf-8"))
    openings = _load_openings()
    topics: list[Topic] = []
    for item in raw:
        tid = item["id"]
        op = openings.get(tid) or {}
        topics.append(
            Topic(
                id=tid,
                title_en=item["title_en"],
                title_zh=item["title_zh"],
                ai_role=item["ai_role"],
                scenario=item["scenario"],
                user_goal=item["user_goal"],
                keywords=tuple(item.get("keywords") or []),
                min_level=int(item.get("min_level") or 1),
                opening_zh=str(op.get("zh") or ""),
                opening_en=str(op.get("en") or ""),
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


def instant_opening(topic: Topic) -> tuple[str, str]:
    """Local canned opening — no LLM. Instant topic start."""
    zh = topic.opening_zh.strip() or f"你好！我们来练习「{topic.title_zh}」吧。你准备好了吗？"
    en = topic.opening_en.strip() or f"Hi! Let's practise “{topic.title_en}”. Ready?"
    return zh, en
