# PHASE 0 — Preparation

## Objective

Prepare the repository and establish development rules.

## Tasks

* [ ] Create the initial monorepo structure.
* [ ] Create `PLAN.md`.
* [ ] Create `AGENTS.md`.
* [ ] Create `.gitignore`.
* [ ] Create `.env.example`.
* [ ] Create `README.md` (minimal).
* [ ] Create the `docs/` directory with `conventions.md` and `decisions.md`.
* [ ] Configure Python environment and tooling (`pyproject.toml`, Ruff, MyPy, Pytest).
* [ ] Create `shared/` with minimal cross-cutting utilities (logging helpers, HTTP error schema).

## Expected Structure

```text
project/
├── core-api/
├── customer-service/
├── product-service/
├── order-service/
├── order-worker/
├── shared/
├── docs/
│   ├── conventions.md
│   └── decisions.md
├── .env.example
├── .gitignore
├── AGENTS.md
├── PLAN.md
└── README.md
```

## Acceptance Criteria

* [ ] Repository structure created.
* [ ] Python tooling configured and executable (`make lint`, `make test` run without errors).
* [ ] No business logic implemented yet.
