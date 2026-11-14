.PHONY: setup data migrate dev test lint bench e2e frontend-install

UV ?= uv
PYTHONPATH := backend
export PYTHONPATH

setup: frontend-install
	$(UV) sync
	@test -f .env || cp .env.example .env
	mkdir -p data data/tts_cache data/cache
	$(MAKE) migrate
	@echo "Setup done. Add a free Gemini key to .env if you want LLM replies."

frontend-install:
	cd frontend && npm install

migrate:
	cd backend && $(UV) run alembic -c alembic.ini upgrade head

data:
	$(UV) run python scripts/fetch_data.py --out data/dictionary.db --cache data/cache

dev:
	@mkdir -p data
	bash scripts/dev.sh

test:
	$(UV) run pytest backend/tests -q
	cd frontend && npm test -- --run

lint:
	$(UV) run ruff check backend
	$(UV) run ruff format --check backend
	$(UV) run mypy
	cd frontend && npm run lint && npx tsc --noEmit

bench:
	$(UV) run python scripts/bench_latency.py

e2e:
	cd frontend && npx playwright test
