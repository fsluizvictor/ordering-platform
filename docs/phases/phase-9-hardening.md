# PHASE 9 — Hardening and Final Documentation

## Objective

Polish, validate quality gates, and ensure the project is ready to present.

## Code

* [ ] Add missing type hints across all services.
* [ ] Review exception handling — no bare `except`, no silent swallowing.
* [ ] Review input validation coverage at HTTP boundary.
* [ ] Remove dead code and unused imports.
* [ ] Run `ruff check .` — zero violations.
* [ ] Run `ruff format .` — no diffs.
* [ ] Run `mypy` — zero errors.

## Security

* [ ] No secrets or credentials in source code.
* [ ] All sensitive config via environment variables.
* [ ] No stack traces in HTTP responses.
* [ ] No internal error details exposed to clients.

## Database

* [ ] Confirm `UNIQUE(email)` constraint on `customer` table.
* [ ] Confirm `UNIQUE(external_id)` constraint on `order` table.
* [ ] Review indexes for common query patterns.

## Docker

* [ ] Health checks configured on all services in `docker-compose.yml`.
* [ ] Restart policies set (`restart: on-failure` or `unless-stopped`).
* [ ] `.env.example` is complete and matches all env vars read by the code.

## README

* [ ] Project objective clear.
* [ ] Architecture diagram present.
* [ ] How to run (`docker compose up`).
* [ ] How to run tests (`make test`).
* [ ] All endpoints listed.
* [ ] Swagger location documented.
* [ ] How to scale workers (`--scale order-worker=3`).
* [ ] Known limitations listed (stock decrement, Redis idempotency).

## Final Validation

```bash
docker compose down -v
docker compose up --build
make test
make lint
make typecheck
```

## Acceptance Criteria

* [ ] `docker compose up --build` starts all services cleanly.
* [ ] All tests pass.
* [ ] Zero linting errors.
* [ ] Zero type errors.
* [ ] README is sufficient to run and understand the project without prior context.
