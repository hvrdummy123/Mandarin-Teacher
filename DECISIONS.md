# Decisions

One-liners for choices the SPEC left open.

- VAD: energy-based FrameVAD instead of webrtcvad — webrtcvad currently fails import (`pkg_resources`) on this Python/setuptools combo; same end-of-speech role.
- Dictionary DB is a separate SQLite file (`data/dictionary.db`) from app state (`data/duihua.db`) so `make data` can rebuild lexicon without wiping sessions.
- Default `LLM_PROVIDERS=gemini,openrouter` (Ollama opt-in) so a fresh clone without API keys correctly fails `/readyz` llm check.
- Python packaging: `uv` with `package = false` and `PYTHONPATH=backend` — avoids fighting hatch over the `backend/app` layout.
- Pin runtime to Python 3.12 via `.python-version` (SPEC allows 3.11+; 3.12 is installed locally and keeps CI off bleeding-edge 3.14).
- Frontend: no TanStack Query in P0; plain fetch later if needed. Zustand only for theme/UI shell state.
- HSK checksum left empty in `fetch_data.py` because the upstream file moves; script prints sha256 for pinning later.
- HSK source: `drkameleon/complete-hsk-vocabulary` (MIT) — the krmanik path in SPEC §3 404s; we take the lowest `new-N` band per word.
- Word "播放" in the hover popover is disabled until P2 TTS; text chat does not need streamed audio yet.
- Gemini/OpenRouter stream() completes then chunks for P1 — real SSE when voice latency budgets matter in P2.
- 不/一 sandhi applied in TextAnalyzer after jieba (and across split tokens) because pypinyin alone is inconsistent on compounds jieba splits.
- Whisper: `language=None` (auto) + Chinese `initial_prompt` instead of SPEC's `language="zh"`, so mixed Mandarin/English still transcribes.
- UI copy is English-first with optional Chinese secondary labels; learner asked for navigable English.
- Progress screen ships in P2 with stub XP (full XP rules remain P3).
- Tone scoring still P5; voice turns persist WAV under `data/audio/{session_id}/` for later scoring.

- Gemini model ids default to `gemini-flash-latest` / `gemini-flash-lite-latest` (aliases); older `gemini-2.0-flash` is shut down. This project's Gemini key still 404s on generateContent in smoke tests — OpenRouter free path works and is the live fallback.
