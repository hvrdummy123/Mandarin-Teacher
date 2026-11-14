"""Settings loading."""

from __future__ import annotations

from app.config import Settings, get_settings


def test_default_bind_is_localhost() -> None:
    get_settings.cache_clear()
    settings = Settings(
        gemini_api_key="",
        openrouter_api_key="",
        llm_providers="gemini",
    )
    assert settings.host == "127.0.0.1"
    assert settings.configured_llm_providers() == []


def test_gemini_counts_as_configured() -> None:
    settings = Settings(
        gemini_api_key="abc",
        openrouter_api_key="",
        llm_providers="gemini,openrouter",
    )
    assert settings.configured_llm_providers() == ["gemini"]
