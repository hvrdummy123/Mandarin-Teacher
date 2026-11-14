# Test report

## Phase 0–1 (earlier)

See git history. Superseded by totals below.

## Phase 2 + UI fixes (2026-11-14)

### Commands

```bash
uv run ruff check backend && uv run ruff format --check backend && uv run mypy
PYTHONPATH=backend uv run pytest backend/tests -q
cd frontend && npm run lint && npx tsc --noEmit && npm test -- --run && npm run build
cd frontend && npx playwright test
PYTHONPATH=backend uv run python scripts/live_smoke.py
```

### Results

| Suite | Result |
| --- | --- |
| Backend pytest | **42 passed** (checklist automation + VAD + prior P1) |
| Ruff + mypy | **pass** |
| Vitest | **4 passed** |
| Playwright e2e | **2 passed** (English rail, distinct screens, mic primary) |
| `scripts/live_smoke.py` (real providers) | **pass** via OpenRouter (Gemini 503 → fallback) |
| Vite build | **pass** |

### Live checklist (real providers)

| Check | Result |
| --- | --- |
| Level 5 + restaurant open + message | **pass** (opening + reply in Chinese) |
| 银行 → yínháng, 不对 → búduì | **pass** (`yín háng` / `bú duì`) |
| Wrong sentence → correction card | **pass** |
| Save word + list again | **pass** |
| Level 60 reply ≠ level 5 | **pass** (len 10 vs 29; harder vocab) |

Gemini returned 503 on this run; OpenRouter free models completed every LLM step. Automated FakeLLM checklist lives in `backend/tests/integration/test_checklist.py`; UI checklist in `frontend/tests/e2e/checklist.spec.ts`.

### Could not verify

- Real microphone push-to-talk end-to-end (AudioWorklet + Whisper load + TTS playback). Whisper is not loaded during `live_smoke` (`load_whisper=False`).
- Hands-free comfort / 20-minute conversation feel.
- Gemini primary path (503 / unavailable; OpenRouter worked).
- Tone scoring (Phase 5); per-turn WAV is saved under `data/audio/{session_id}/` for later.
- CI on a clean remote runner.
