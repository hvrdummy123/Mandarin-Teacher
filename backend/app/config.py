"""Application settings from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(value: Path | str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'duihua.db'}"

    gemini_api_key: str = ""
    gemini_reply_model: str = "gemini-flash-latest"
    gemini_analysis_model: str = "gemini-flash-lite-latest"

    openrouter_api_key: str = ""
    openrouter_reply_model: str = "openrouter/free"
    openrouter_analysis_model: str = "openrouter/free"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_reply_model: str = "qwen2.5:7b"
    ollama_analysis_model: str = "qwen2.5:7b"

    # Ollama is opt-in so a fresh clone without API keys stays "not ready" for LLM.
    llm_providers: str = "gemini,openrouter"

    whisper_model_size: str = "small"
    whisper_compute_type: str = "int8"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_cache_dir: Path = Path("data/tts_cache")

    data_dir: Path = Path("data")
    dictionary_db_path: Path = Path("data/dictionary.db")

    log_level: str = "INFO"
    timezone: str = "Asia/Shanghai"
    daily_xp_goal: int = 100
    level_out_of_vocab_threshold: float = 0.12
    upload_max_bytes: int = 8 * 1024 * 1024
    audio_max_seconds: int = 60

    # Readiness flags flipped by the composition root once heavy assets load.
    whisper_loaded: bool = Field(default=False, exclude=True)
    dictionary_loaded: bool = Field(default=False, exclude=True)

    @field_validator("data_dir", "dictionary_db_path", "tts_cache_dir", mode="before")
    @classmethod
    def _paths_relative_to_repo(cls, value: object) -> Path:
        return _resolve_path(value if isinstance(value, (str, Path)) else Path("data"))

    @field_validator("database_url", mode="before")
    @classmethod
    def _sqlite_relative_to_repo(cls, value: object) -> str:
        if not isinstance(value, str):
            return str(value)
        prefix = "sqlite:///"
        if value.startswith(prefix) and not value.startswith("sqlite:////"):
            raw = value[len(prefix) :]
            if raw != ":memory:" and not Path(raw).is_absolute():
                return prefix + str((REPO_ROOT / raw).resolve())
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_provider_list(self) -> list[str]:
        return [p.strip().lower() for p in self.llm_providers.split(",") if p.strip()]

    def configured_llm_providers(self) -> list[str]:
        """Providers that have enough config to attempt a call."""
        ready: list[str] = []
        for name in self.llm_provider_list:
            gemini_ok = name == "gemini" and bool(self.gemini_api_key)
            openrouter_ok = name == "openrouter" and bool(self.openrouter_api_key)
            # Ollama needs no key; a base URL means "configured".
            ollama_ok = name == "ollama" and bool(self.ollama_base_url)
            if gemini_ok or openrouter_ok or ollama_ok:
                ready.append(name)
        return ready


@lru_cache
def get_settings() -> Settings:
    return Settings()
