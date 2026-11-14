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
- Word/sentence replay uses `POST /api/tts` (same Edge TTS voice + disk cache as chat replies).
- Gemini/OpenRouter stream() completes then chunks for P1 — real SSE when voice latency budgets matter in P2.
- 不/一 sandhi applied in TextAnalyzer after jieba (and across split tokens) because pypinyin alone is inconsistent on compounds jieba splits.
- Whisper: `language=None` (auto) + Chinese `initial_prompt` instead of SPEC's `language="zh"`, so mixed Mandarin/English still transcribes.
- UI copy is English-first with optional Chinese secondary labels; learner asked for navigable English.
- Progress screen ships in P2 with stub XP (full XP rules remain P3).
- Tone scoring still P5; voice turns persist WAV under `data/audio/{session_id}/` for later scoring.

- Gemini model ids default to `gemini-flash-latest` / `gemini-flash-lite-latest` (aliases); older `gemini-2.0-flash` is shut down. This project's Gemini key still 404s on generateContent in smoke tests — OpenRouter free path works and is the live fallback.
- Audio fixtures live under `backend/tests/e2e_audio/fixtures/` (edge-tts → ffmpeg 16 kHz mono WAV); `gen_audio_fixtures.py --check` runs real faster-whisper CER.
- `bench_latency.py` defaults to real Whisper/TTS/LLM; `--fake-llm` isolates local costs per SPEC §15.
- Live while-speaking captions use browser SpeechRecognition (zh-CN) + `POST /api/enrich` for pinyin/rough English; final turn still uses Whisper + LLM (SPEC allows BrowserSTT as fast path).
- Mic is tap-to-toggle (not hold); VAD auto-end only when `hands_free: true` so short taps are not cut off.
- Speed: keep SQLite (not the bottleneck). OpenRouter-first + 12s LLM timeout + breaker on first 429. Whisper `base` + MPS on Apple Silicon. Voice turns prefer browser `heard_hint` over Whisper when present; skip level regenerations; TTS overlaps analysis.
- Topic start is instant via canned `topic_openings.json` (no LLM). Conversation turns still use the LLM.
- SQLite lock fix: `busy_timeout=30s` + commit message rows before LLM/TTS awaits so writers do not hold the DB during network I/O.
- LLM breakers: 2 failures / 45s recovery, but if every provider is open we force a half-open probe so chat never soft-locks on “no providers available”.
- Topic analysis always offers an “I think you meant…” correction when the learner is off-goal or STT-garbled; tone/pronunciation coaching stays Phase 5.
- On free-tier 429, do not invent offline AI replies — keep the learner’s line, show a retry message, wait for real providers.
- Reply prompts include the last ~8 turns so the model stays in topic/conversation context.
- Optional UI “Review before send”: speak → confirm/discard transcript (with pinyin/hanzi/English) before calling the AI.
- STT cannot be fully “trained” in-browser; we repair common mix-ups with topic bias (借口→家, 名词→名字) + Whisper topic prompt. OpenRouter uses several :free models so one 429 does not end the turn.
