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
| Backend unit + integration | **10 passed** |
| Ruff check + format | **pass** |
| mypy strict on `app/` | **pass** |
| Frontend eslint | **pass** |
| `tsc --noEmit` | **pass** |
| Vitest (Shell) | **1 passed** |
| Vite production build | **pass** (JS gzip ≈ 47 KB) |
| `make data` / fetch_data | **pass** — 125413 CC-CEDICT rows, 11470 HSK rows |
| `/healthz` | **ok** |
| `/readyz` | **503** as expected without Whisper load + LLM keys; `database` + `dictionary` true |

### Could not verify

- Real microphone / browser push-to-talk (no voice stack yet).
- Whisper model load (P2).
- Live Gemini / OpenRouter / Ollama calls (no keys required for P0; `/readyz` llm check correctly false without keys).
- GitHub Actions CI on a clean runner (workflow file is present; not executed here).
- `make dev` full interactive session (script exists; API smoke-tested separately).
