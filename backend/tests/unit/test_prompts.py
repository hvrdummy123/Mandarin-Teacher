"""Prompt template snapshots — catch accidental edits."""

from __future__ import annotations

from app.prompts.loader import load_prompt, render


def test_reply_prompt_snapshot() -> None:
    text = load_prompt("reply.txt")
    assert "Simplified Chinese only" in text
    assert "{{level}}" in text
    assert "{{topic_block}}" in text
    rendered = render(
        "reply.txt",
        level=5,
        hsk_band=1,
        max_chars=20,
        topic_block="Topic: cafe",
        vocab_hint="你好",
        saved_words="咖啡",
        forbidden_block="",
    )
    assert "{{" not in rendered
    assert "Level: 5" in rendered


def test_analysis_prompt_snapshot() -> None:
    text = load_prompt("analysis.txt")
    assert "JSON only" in text
    assert "goal_progress" in text
    assert "{{user_text}}" in text
