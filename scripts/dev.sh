#!/usr/bin/env bash
# Start API + Vite together for local work.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p data

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then kill "$API_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

export PYTHONPATH=backend
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload &
API_PID=$!

cd frontend
npm run dev
