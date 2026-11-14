# Test report

## Phase 0

Commands run (2026-11-14, local macOS, Python 3.12 via uv, Node 22):

```bash
uv sync --group dev
uv run ruff check backend
uv run ruff format --check backend
uv run mypy
PYTHONPATH=backend uv run pytest backend/tests -q
cd frontend && npm install && npm run lint && npx tsc --noEmit && npm test -- --run && npm run build
uv run python scripts/fetch_data.py --out data/dictionary.db --cache data/cache
# smoke: uvicorn on :8010 → GET /healthz, GET /readyz
```

| Suite | Result |
| --- | --- |
| Backend unit + integration | **10 passed** (P0 baseline; superseded by P1 totals below) |
| Ruff / mypy | **pass** |
| Frontend | **pass** |
| `make data` | **pass** |

### Could not verify (P0)

- Real microphone / Whisper / live LLM; CI on a clean runner; full interactive `make dev`.

---

## Phase 1

Commands run (2026-11-14):

```bash
uv run ruff check backend && uv run ruff format --check backend && uv run mypy
PYTHONPATH=backend uv run pytest backend/tests -q \
  --cov=backend/app/domain --cov=backend/app/application --cov-report=term-missing
cd frontend && npm run lint && npx tsc --noEmit && npm test -- --run && npm run build
```

| Suite | Result |
| --- | --- |
| Backend tests | **35 passed** |
| domain/ + application/ coverage | **90%** (target ≥85%) |
| Ruff + mypy | **pass** |
| Frontend eslint / tsc | **pass** |
| Vitest | **4 passed** (Shell toggles, RubyText, tones) |
| Vite build | **pass** (JS gzip ≈ 51 KB) |

### Could not verify (P1)

- Live Gemini / OpenRouter / Ollama replies (tests use `FakeLLM`; adapters are wired but not called without keys).
- Hover "播放" TTS (deferred to P2; button disabled).
- Playwright e2e text-chat flow (SPEC lists broader e2e later; P1 covered by Vitest + REST integration).
- GitHub Actions on a clean runner.
