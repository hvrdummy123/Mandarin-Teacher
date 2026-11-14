# Decisions

One-liners for choices the SPEC left open.

- VAD: use `webrtcvad` for now (SPEC allows it as the lighter option); can swap to Silero+onnxruntime in P2 if quality needs it.
- Dictionary DB is a separate SQLite file (`data/dictionary.db`) from app state (`data/duihua.db`) so `make data` can rebuild lexicon without wiping sessions.
- Default `LLM_PROVIDERS=gemini,openrouter` (Ollama opt-in) so a fresh clone without API keys correctly fails `/readyz` llm check.
- Python packaging: `uv` with `package = false` and `PYTHONPATH=backend` — avoids fighting hatch over the `backend/app` layout.
- Pin runtime to Python 3.12 via `.python-version` (SPEC allows 3.11+; 3.12 is installed locally and keeps CI off bleeding-edge 3.14).
- Frontend: no TanStack Query in P0; plain fetch later if needed. Zustand only for theme/UI shell state.
- HSK checksum left empty in `fetch_data.py` because the upstream file moves; script prints sha256 for pinning later.
- HSK source: `drkameleon/complete-hsk-vocabulary` (MIT) — the krmanik path in SPEC §3 404s; we take the lowest `new-N` band per word.

- Gemini model ids in `.env.example` are snapshots (`gemini-2.0-flash` / `flash-lite`); free-tier names change — verify against Google docs when wiring P1.
