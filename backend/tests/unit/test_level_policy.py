"""Level policy and post-check."""

from __future__ import annotations

import pytest

from app.domain.level import (
    enforce_level_on_reply,
    level_for_tier,
    rules_for_level,
    share_out_of_level,
    tier_for_level,
    vocab_size_is_monotonic,
)


def test_vocab_size_monotonic() -> None:
    assert vocab_size_is_monotonic()
    assert rules_for_level(1).vocab_size == 150
    assert rules_for_level(100).vocab_size >= 10000


def test_tier_mapping() -> None:
    assert tier_for_level(1) == 1
    assert tier_for_level(10) == 1
    assert tier_for_level(11) == 2
    assert level_for_tier(3) == 21


@pytest.mark.asyncio
async def test_postcheck_accepts_in_level() -> None:
    allowed = {"你好", "今天", "怎么样"}
    calls: list[list[str]] = []

    async def gen(forbidden: list[str]) -> str:
        calls.append(forbidden)
        return "你好"

    result = await enforce_level_on_reply(
        gen,
        first_reply="你好今天怎么样",
        allowed=allowed,
        keywords=set(),
        threshold=0.12,
    )
    assert result.regenerated is False
    assert result.text == "你好今天怎么样"
    assert calls == []


@pytest.mark.asyncio
async def test_postcheck_regenerates_once_then_accepts() -> None:
    allowed = {"你好"}
    calls: list[list[str]] = []

    async def gen(forbidden: list[str]) -> str:
        calls.append(list(forbidden))
        # Still uses a hard word — should be accepted and marked.
        return "你好 复杂"

    result = await enforce_level_on_reply(
        gen,
        first_reply="你好 复杂 困难",
        allowed=allowed,
        keywords=set(),
        threshold=0.12,
    )
    assert result.regenerated is True
    assert len(calls) == 1
    assert "复杂" in calls[0] or "困难" in calls[0]
    assert "复杂" in result.out_of_level


def test_exempts_keywords_and_proper_nouns() -> None:
    allowed = {"你好"}
    share, bad = share_out_of_level(
        "你好 菜单 Beijing",
        allowed=allowed,
        keywords={"菜单"},
    )
    assert "菜单" not in bad
    assert "Beijing" not in bad
    assert share == 0.0
