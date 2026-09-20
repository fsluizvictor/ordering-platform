.PHONY: lint format typecheck test install seed seed-sql

install:
	python -m pip install -r requirements-dev.txt

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy

test:
	pytest

# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

## seed: Popula o banco via Core API (requer containers rodando)
seed:
	python scripts/seed.py

## seed-sql: Popula o banco diretamente via SQL no container PostgreSQL (fallback)
seed-sql:
	docker compose exec -T postgres psql -U ordering -f /dev/stdin < scripts/seed.sql
