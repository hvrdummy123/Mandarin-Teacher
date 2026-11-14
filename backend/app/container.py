"""Composition root — wire adapters here, nowhere else."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.dictionary.sqlite_repo import CedictSqliteRepo
from app.adapters.llm.fallback import FallbackChain
from app.adapters.llm.gemini import GeminiAdapter
from app.adapters.llm.ollama import OllamaAdapter
from app.adapters.llm.openrouter import OpenRouterAdapter
from app.adapters.persistence.db import create_db_engine, make_session_factory
from app.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter
from app.adapters.tts.edge import EdgeTTSAdapter
from app.application.chat import ChatServices
from app.application.text_analyzer import TextAnalyzer
from app.config import Settings, get_settings
from app.logging import get_logger
from app.ports.dictionary import DictionaryRepo
from app.ports.llm import LLMProvider

log = get_logger(__name__)


@dataclass
class AppState:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    dictionary: DictionaryRepo | None = None
    llm: FallbackChain | None = None
    chat_services: ChatServices | None = None
    stt: FasterWhisperAdapter | None = None
    tts: EdgeTTSAdapter | None = None
    timings: list[dict[str, object]] = field(default_factory=list)

    def refresh_readiness_flags(self) -> None:
        dict_path = Path(self.settings.dictionary_db_path)
        self.settings.dictionary_loaded = dict_path.is_file() and dict_path.stat().st_size > 0
        if self.stt is not None:
            self.settings.whisper_loaded = self.stt.loaded


def build_llm_chain(settings: Settings, extra: list[LLMProvider] | None = None) -> FallbackChain:
    providers: list[LLMProvider] = list(extra or [])
    for name in settings.llm_provider_list:
        if name == "gemini" and settings.gemini_api_key:
            providers.append(
                GeminiAdapter(
                    settings.gemini_api_key,
                    reply_model=settings.gemini_reply_model,
                    analysis_model=settings.gemini_analysis_model,
                    timeout_s=settings.llm_timeout_s,
                )
            )
        elif name == "openrouter" and settings.openrouter_api_key:
            reply_models = [
                m.strip() for m in settings.openrouter_reply_model.split(",") if m.strip()
            ]
            analysis_models = [
                m.strip() for m in settings.openrouter_analysis_model.split(",") if m.strip()
            ]
            if not reply_models:
                reply_models = ["qwen/qwen-2.5-7b-instruct:free"]
            if not analysis_models:
                analysis_models = reply_models
            # One adapter per model so a 429 on model A still allows model B.
            for i, reply_model in enumerate(reply_models):
                analysis_model = analysis_models[min(i, len(analysis_models) - 1)]
                short = reply_model.split("/")[-1][:24]
                providers.append(
                    OpenRouterAdapter(
                        settings.openrouter_api_key,
                        name=f"openrouter:{short}",
                        reply_model=reply_model,
                        analysis_model=analysis_model,
                        timeout_s=settings.llm_timeout_s,
                    )
                )
        elif name == "ollama" and settings.ollama_base_url:
            providers.append(
                OllamaAdapter(
                    settings.ollama_base_url,
                    reply_model=settings.ollama_reply_model,
                    analysis_model=settings.ollama_analysis_model,
                )
            )
    return FallbackChain(providers=providers)


def build_chat_services(
    settings: Settings,
    dictionary: DictionaryRepo,
    llm: FallbackChain,
) -> ChatServices:
    ranked: list[str] = []
    if isinstance(dictionary, CedictSqliteRepo):
        try:
            ranked = dictionary.words_by_hsk_then_freq(12000)
        except Exception:
            ranked = []
    from app.adapters.dictionary.memory import MemoryDictionary

    if not ranked and isinstance(dictionary, MemoryDictionary):
        ranked = sorted(dictionary.hsk.keys(), key=lambda w: (dictionary.hsk[w], w))

    return ChatServices(
        llm=llm,
        analyzer=TextAnalyzer(dictionary),
        ranked_vocab=ranked,
        out_of_vocab_threshold=settings.level_out_of_vocab_threshold,
    )


def build_container(
    settings: Settings | None = None,
    *,
    llm: FallbackChain | None = None,
    dictionary: DictionaryRepo | None = None,
    load_whisper: bool = True,
) -> AppState:
    settings = settings or get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.tts_cache_dir).mkdir(parents=True, exist_ok=True)

    engine = create_db_engine(settings)
    session_factory = make_session_factory(engine)
    state = AppState(settings=settings, engine=engine, session_factory=session_factory)

    if dictionary is None and Path(settings.dictionary_db_path).is_file():
        try:
            dictionary = CedictSqliteRepo(Path(settings.dictionary_db_path))
            dictionary.connect()
        except Exception as exc:
            log.warning("dictionary_load_failed", error=str(exc))
            dictionary = None

    state.dictionary = dictionary
    state.llm = llm or build_llm_chain(settings)
    if dictionary is not None and state.llm is not None:
        state.chat_services = build_chat_services(settings, dictionary, state.llm)

    state.tts = EdgeTTSAdapter(
        voice=settings.tts_voice,
        cache_dir=Path(settings.tts_cache_dir),
    )
    state.stt = FasterWhisperAdapter(
        model_size=settings.whisper_model_size,
        compute_type=settings.whisper_compute_type,
        device=settings.whisper_device,
        download_root=Path(settings.data_dir) / "whisper",
    )
    # Lazy-load Whisper on first use (or eagerly if load_whisper and not in tests).
    if load_whisper:
        try:
            state.stt.load()
        except Exception as exc:
            log.warning("whisper_load_failed", error=str(exc))

    state.refresh_readiness_flags()
    log.info(
        "container_ready",
        dictionary_loaded=settings.dictionary_loaded,
        whisper_loaded=settings.whisper_loaded,
        llm_providers=settings.configured_llm_providers(),
        chat_ready=state.chat_services is not None,
    )
    return state
