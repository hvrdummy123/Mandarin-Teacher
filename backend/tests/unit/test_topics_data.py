"""Static data files shipped with the scaffold."""

from __future__ import annotations

import json
from pathlib import Path

BACKEND_DATA = Path(__file__).resolve().parents[2] / "data"


def test_exactly_thirty_topics() -> None:
    topics = json.loads((BACKEND_DATA / "topics.json").read_text(encoding="utf-8"))
    assert len(topics) == 30
    ids = [t["id"] for t in topics]
    assert len(ids) == len(set(ids))
    required = {
        "id",
        "title_en",
        "title_zh",
        "ai_role",
        "scenario",
        "user_goal",
        "keywords",
        "min_level",
    }
    for topic in topics:
        assert required.issubset(topic.keys())


def test_level_curve_json_loads() -> None:
    curve = json.loads((BACKEND_DATA / "level_curve.json").read_text(encoding="utf-8"))
    assert "defaults" in curve
    assert curve["defaults"]["vocab_n1"] == 150
