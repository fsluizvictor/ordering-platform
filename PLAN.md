# PLAN.md

# Online Sales Platform — Implementation Plan

## 1. Objective

This document defines the implementation plan for the Online Sales Platform.

The goal is to incrementally implement the architecture defined in `arquitetura_requisitos_projeto.md`, using:

* Python
* Flask
* SQLAlchemy
* PostgreSQL
* Redis
* RabbitMQ
* Pika
* Pytest
* Docker
* Docker Compose
* OpenAPI/Swagger

The solution will be organized as a monorepo containing five main components:

```text
project/
├── core-api/
├── customer-service/
├── product-service/
├── order-service/
├── order-worker/
├── shared/
├── docs/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── AGENTS.md
├── PLAN.md
└── README.md
```

The implementation must follow Hexagonal Architecture, keeping the domain and application layers decoupled from infrastructure technologies.

---

# 2. Execution Rules

These rules must be followed throughout the entire implementation.

## 2.1 Incremental Development

Do not implement the entire project at once.

Each phase must:

1. be implemented;
2. have its tests written;
3. have its tests executed;
4. have its acceptance criteria verified;
5. only then allow the next phase to begin.

Do not automatically start a subsequent phase.

---

## 2.2 Architecture

All services must follow Hexagonal Architecture.

Conceptual structure:

```text
Domain
   |
Application
   |
   +---- Inbound Adapters
   |
   +---- Outbound Adapters
```

The domain must not directly depend on:

* Flask;
* SQLAlchemy;
* PostgreSQL;
* Redis;
* RabbitMQ;
* Pika;
* Docker.

Infrastructure dependencies must be accessed through ports/interfaces.

---

## 2.3 Separation of Responsibilities

Each microservice must be responsible exclusively for its own domain.

Do not share domain entities between microservices.

Code sharing must be minimal and limited to genuinely generic components.

---

## 2.4 Core API

The Core API must:

* be stateless;
* be the only public HTTP entry point;
* have no database of its own;
* perform routing;
* perform initial validation;
* handle errors;
* generate/propagate correlation IDs;
* communicate with internal services;
* provide Swagger/OpenAPI documentation.

Do not place Order business rules inside the Core API.

---

## 2.5 PostgreSQL

PostgreSQL is the source of truth for persisted data.

Redis must not be used as the primary database.

Database integrity constraints must include:

```text
UNIQUE(email)        — Customer
UNIQUE(external_id)  — Order
```

---

## 2.6 Redis

Redis will be used for:

* Customer caching;
* Product caching.

The cache strategy must be Cache-Aside.

> **Future work:** Redis `NX + TTL` for idempotency protection at the messaging layer
> (see `docs/decisions.md` — Idempotency).

---

## 2.7 RabbitMQ

RabbitMQ will be used for asynchronous Order processing.

The main event will be:

```text
OrderCreated
```

The Order Worker must use manual ACK.

A message may only be acknowledged after successful processing and persistence.

Retry and DLQ must be configured at queue declaration level (dead-letter exchange).
After the retry limit, messages must be routed to a Dead Letter Queue.

---

## 2.8 Idempotency

Idempotency is enforced by `UNIQUE(external_id)` at the database level.

The database will reject duplicate Orders at the persistence layer.

```text
PostgreSQL UNIQUE(external_id)
```

> **Future work:** Add Redis `NX + TTL` and `Idempotency-Key` header as an additional
> protection layer before message processing reaches the database.
> Document in `docs/decisions.md` when implemented.

---

## 2.9 Order Database Ownership

The Order Service and the Order Worker share the same PostgreSQL Order database.

Responsibilities:
- **Order Worker** — writes (creates, updates Order status and items).
- **Order Service** — reads (queries Orders by external_id, list, count).

They are separate processes but belong to the same business context.

---

## 2.10 Stock Behaviour

The Order Worker validates that `quantity <= stock` before processing.

Stock is **not decremented** after an Order is completed in this phase.
Stock decrement is deferred as future work and must be explicitly requested before implementation.

---

## 2.11 Testing Strategy

| Service | Unit Tests | Integration Tests |
|---|---|---|
| Customer Service | Yes — all domain rules | No |
| Product Service | Yes — all domain rules | No |
| Core API | Yes — routing, validation, error handling | No |
| Order Service | Yes — domain rules, HTTP | Yes — 1 happy path |
| Order Worker | Yes — processing logic | Yes — 1 happy path |

Unit tests must cover all business rules independently from infrastructure.

Integration tests use real infrastructure (PostgreSQL, Redis, RabbitMQ) via Docker Compose.

---

# 3. Implementation Phases

---

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
* [ ] Configure Python environment and tooling (`pyproject.toml`, Ruff, Black, MyPy, Pytest).
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
* [ ] Python tooling configured and executable.
* [ ] No business logic implemented yet.

---

# PHASE 1 — Docker Infrastructure

## Objective

Start the infrastructure services needed by all other phases.

Only infrastructure containers are defined here. Each application service adds its own
Dockerfile in its own phase.

## Containers (this phase)

```text
postgres
redis
rabbitmq
```

## Tasks

* [ ] Create `docker-compose.yml` with infrastructure services only.
* [ ] Configure PostgreSQL (databases, credentials via env vars).
* [ ] Configure Redis.
* [ ] Configure RabbitMQ (management plugin, credentials via env vars).
* [ ] Configure named volumes.
* [ ] Configure a shared network for all services.
* [ ] Configure health checks for postgres, redis, rabbitmq.
* [ ] Complete `.env.example` with all infrastructure variables.

## Acceptance Criteria

Run:

```bash
docker compose up postgres redis rabbitmq
```

All three infrastructure containers must start and report healthy.

---

# PHASE 2 — Customer Service

## Objective

Fully implement the Customer domain with HTTP API and persistence.

## Entity

```text
Customer
├── id: UUID
├── name: string
├── email: string
├── phone: string
├── created_at: datetime
└── updated_at: datetime
```

## Business Rules

* [ ] `name` is required and must not be empty.
* [ ] `email` is required.
* [ ] `email` must be unique (`UNIQUE` constraint in PostgreSQL).

## Architecture

```text
customer-service/
├── src/customer_service/
│   ├── domain/
│   │   ├── entities/
│   │   ├── ports/
│   │   └── exceptions/
│   ├── application/
│   │   └── services/
│   ├── adapters/
│   │   ├── inbound/
│   │   │   └── http/
│   │   └── outbound/
│   │       └── persistence/
│   ├── config/
│   └── main.py
├── tests/
│   └── unit/
├── Dockerfile
└── pyproject.toml
```

## Endpoints

```http
POST   /customers
GET    /customers
GET    /customers/{id}
GET    /customers/name/{name}
PUT    /customers/{id}
DELETE /customers/{id}
GET    /customers/count
```

## Tests (unit only)

* [ ] Create Customer with valid data.
* [ ] Reject empty name.
* [ ] Reject missing email.
* [ ] Reject duplicate email (domain rule + repository error handling).
* [ ] Find Customer by ID — found.
* [ ] Find Customer by ID — not found.
* [ ] Find Customer by name.
* [ ] Update Customer.
* [ ] Delete Customer.
* [ ] Count Customers.
* [ ] HTTP 201, 200, 404, 409, 422 responses.

## Docker

* [ ] Add `customer-service` to `docker-compose.yml`.
* [ ] Customer Service must depend on `postgres` health check.

## Acceptance Criteria

Customer Service works independently.
All unit tests pass.
Service starts and responds via Docker Compose.

---

# PHASE 3 — Product Service

## Objective

Fully implement the Product domain with HTTP API and persistence.

## Entity

```text
Product
├── id: UUID
├── name: string
├── description: string
├── price: Decimal
├── stock: integer
├── created_at: datetime
└── updated_at: datetime
```

## Business Rules

* [ ] `name` is required and must not be empty.
* [ ] `price` must be greater than zero.
* [ ] `stock` must be greater than or equal to zero.

## Architecture

Same structure as Customer Service, scoped to `product_service` package.

## Endpoints

```http
POST   /products
GET    /products
GET    /products/{id}
GET    /products/name/{name}
PUT    /products/{id}
DELETE /products/{id}
GET    /products/count
```

## Tests (unit only)

* [ ] Create Product with valid data.
* [ ] Reject empty name.
* [ ] Reject price <= 0.
* [ ] Reject negative stock.
* [ ] Find Product by ID — found.
* [ ] Find Product by ID — not found.
* [ ] Find Product by name.
* [ ] Update Product.
* [ ] Delete Product.
* [ ] Count Products.
* [ ] HTTP 201, 200, 404, 422 responses.

## Docker

* [ ] Add `product-service` to `docker-compose.yml`.
* [ ] Product Service must depend on `postgres` health check.

## Acceptance Criteria

Product Service works independently.
All unit tests pass.
Service starts and responds via Docker Compose.

---

# PHASE 4 — Core API

## Objective

Create the single public HTTP entry point, proxying Customer and Product services,
with Swagger/OpenAPI documentation.

## Responsibilities

* Routing requests to Customer Service and Product Service.
* Initial request validation.
* Error handling and consistent error responses.
* Generating and propagating `X-Correlation-ID`.
* Structured logging.
* Swagger/OpenAPI documentation.
* Health check endpoint.

## Rules

* No database.
* No business rules.
* Stateless.
* Must not access PostgreSQL or Redis directly.

## Routes

```text
/customers  → Customer Service
/products   → Product Service
/orders     → Order Service (wired in Phase 5)
```

## Error Response Format

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Customer not found",
    "request_id": "uuid"
  }
}
```

## Tests (unit only)

* [ ] Correct routing to internal service.
* [ ] Correlation ID generated when absent.
* [ ] Correlation ID forwarded when present.
* [ ] 4xx responses from internal services are translated correctly.
* [ ] 5xx responses from internal services return a safe error.
* [ ] Health check returns 200.

## Docker

* [ ] Add `core-api` to `docker-compose.yml`.
* [ ] Core API must depend on `customer-service` and `product-service` health checks.

## Acceptance Criteria

A request to `Core API /customers` is routed to `Customer Service` and returns the correct response.
A request to `Core API /products` is routed to `Product Service` and returns the correct response.
Swagger UI is accessible at `/docs`.
All unit tests pass.

---

# PHASE 5 — Order Service

## Objective

Implement the Order domain and HTTP entry point.
At the end of this phase, `POST /orders` returns `202 Accepted` and publishes `OrderCreated` to RabbitMQ.

## Entities

```text
Order
├── id: UUID
├── external_id: UUID (UNIQUE)
├── customer_id: UUID
├── status: PENDING | PROCESSING | COMPLETED | FAILED
├── total_amount: Decimal
├── created_at: datetime
└── updated_at: datetime
```

```text
OrderItem
├── id: UUID
├── order_id: UUID
├── product_id: UUID
├── quantity: integer
└── unit_price: Decimal
```

## Business Rules

* [ ] Order must contain at least one item.
* [ ] Quantity per item must be greater than zero.
* [ ] `external_id` must be unique (enforced by `UNIQUE` constraint in PostgreSQL).
* [ ] Status transitions: PENDING → PROCESSING → COMPLETED | FAILED.
* [ ] Total is calculated by the system at processing time.
* [ ] `unit_price` stores the price at processing time (set by the Worker).

## OrderCreated Event Payload

```json
{
  "event_id": "uuid",
  "event_type": "OrderCreated",
  "occurred_at": "2026-01-01T12:00:00Z",
  "correlation_id": "uuid",
  "external_id": "uuid",
  "customer_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 2
    }
  ]
}
```

## HTTP Endpoints

```http
POST   /orders          → publish OrderCreated, return 202 Accepted
GET    /orders          → list Orders (reads from Order DB)
GET    /orders/{external_id}
GET    /orders/count
PUT    /orders/{external_id}
DELETE /orders/{external_id}
```

## Response for POST /orders

```http
HTTP 202 Accepted
```

```json
{
  "external_id": "uuid",
  "status": "PENDING"
}
```

## Architecture

```text
order-service/
├── src/order_service/
│   ├── domain/
│   │   ├── entities/
│   │   ├── ports/
│   │   └── exceptions/
│   ├── application/
│   │   └── services/
│   ├── adapters/
│   │   ├── inbound/
│   │   │   └── http/
│   │   └── outbound/
│   │       ├── persistence/
│   │       └── messaging/
│   ├── config/
│   └── main.py
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
└── pyproject.toml
```

> The Order Service and Order Worker share the same PostgreSQL Order database.
> Order Service reads; Order Worker writes.

## Tests

### Unit Tests

* [ ] Order with no items is rejected.
* [ ] Item with quantity zero is rejected.
* [ ] Status transitions are valid.
* [ ] `external_id` is generated on creation.
* [ ] `event_id` and `occurred_at` are set on the event.
* [ ] Correlation ID is propagated to the event.
* [ ] HTTP 202 returned on valid request.
* [ ] HTTP 422 returned on invalid request.

### Integration Test — Happy Path

* [ ] `POST /orders` with valid payload returns 202.
* [ ] `OrderCreated` message is present in RabbitMQ queue.
* [ ] `GET /orders/{external_id}` returns the Order with status `PENDING`.

## Docker

* [ ] Add `order-service` to `docker-compose.yml`.
* [ ] Depends on `postgres` and `rabbitmq` health checks.
* [ ] Wire Core API route `/orders` to Order Service.

## Acceptance Criteria

`POST /orders` returns `202 Accepted` with `external_id`.
`OrderCreated` is published to RabbitMQ.
All unit tests pass.
Integration happy path passes.

---

# PHASE 6 — Order Worker

## Objective

Implement asynchronous Order processing with:
- RabbitMQ consumer with manual ACK.
- Redis Cache-Aside for Customer and Product lookups.
- Business validation and persistence.
- Minimal Retry and Dead Letter Queue.

## Processing Flow

```text
RabbitMQ
   |
   v
Order Worker
   |
   +-- Redis HIT ---------> Customer/Product data
   |
   +-- Redis MISS --------> Customer/Product Service
                                  |
                                  v
                               Redis (populate)
   |
   v
Validate Customer exists
Validate Products exist
Validate quantity <= stock
Calculate total_amount
Persist Order + OrderItems
Update Order status → COMPLETED
   |
   v
ACK
```

## Retry and DLQ (minimal)

The queue is declared with a dead-letter exchange.

```text
RabbitMQ
   |
   v
Worker
   |
   +-- success --> COMMIT --> ACK
   |
   +-- failure --> retry_count < MAX_RETRIES --> NACK (requeue)
                |
                +-- retry_count >= MAX_RETRIES --> NACK (no requeue) --> DLQ
```

Implementation approach:
- `x-dead-letter-exchange` configured at queue declaration.
- Retry counter tracked via message header `x-retry-count`.
- `MAX_RETRIES` configurable via environment variable.
- NACK with `requeue=False` when limit is exceeded (message routes to DLQ automatically).

ACK is only sent after the database transaction has been successfully committed.

## Cache

Customer and Product lookups use Cache-Aside.

```text
Redis
  |
  +-- HIT --> return cached data
  |
  +-- MISS --> call Customer/Product Service HTTP
                    |
                    v
                 Redis SET (with TTL)
                    |
                    v
                 return data
```

Cache is invalidated on Customer/Product update (in their respective services).

## Architecture

```text
order-worker/
├── src/order_worker/
│   ├── domain/           (shared with order-service, or copied)
│   ├── application/
│   │   └── services/
│   ├── adapters/
│   │   ├── inbound/
│   │   │   └── messaging/  (RabbitMQ consumer)
│   │   └── outbound/
│   │       ├── persistence/
│   │       ├── cache/       (Redis)
│   │       └── external_services/ (HTTP clients)
│   ├── config/
│   └── main.py
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
└── pyproject.toml
```

## Tests

### Unit Tests

* [ ] Customer not found → Order status set to FAILED.
* [ ] Product not found → Order status set to FAILED.
* [ ] Quantity exceeds stock → Order status set to FAILED.
* [ ] Total is calculated correctly from items and prices.
* [ ] `unit_price` is stored per item.
* [ ] Cache HIT returns cached data without calling external service.
* [ ] Cache MISS calls external service and populates cache.
* [ ] Message is ACKed only after successful commit.
* [ ] Message is NACKed when retry limit is exceeded.

### Integration Test — Happy Path

* [ ] Publish a valid `OrderCreated` message to RabbitMQ.
* [ ] Worker processes the message.
* [ ] Order is persisted in PostgreSQL with status `COMPLETED`.
* [ ] Order items are persisted with correct `unit_price`.
* [ ] Message is ACKed (queue is empty after processing).

## Docker

* [ ] Add `order-worker` to `docker-compose.yml`.
* [ ] Depends on `postgres`, `redis`, `rabbitmq` health checks.
* [ ] Worker scaling must work: `docker compose up --scale order-worker=3`.

## Acceptance Criteria

Full async flow works end to end:
```text
POST /orders → 202 → RabbitMQ → Worker → PostgreSQL (COMPLETED)
```
All unit tests pass.
Integration happy path passes.
DLQ receives messages after retry limit is exceeded.

---

# PHASE 7 — Observability (essential only)

## Objective

Enable traceability across the full request and async processing flow.
Scope is intentionally minimal: structured logging and correlation ID propagation only.

## Correlation ID

Header:

```http
X-Correlation-ID: <uuid>
```

Flow:

```text
Client
  ↓ (generates if absent)
Core API
  ↓ (forwards header)
Order Service
  ↓ (embeds in event payload)
RabbitMQ
  ↓ (reads from event)
Order Worker
```

## Structured Logging

Use Python's standard `logging` module with a JSON formatter.
No additional libraries unless already in the project.

Log format:

```json
{
  "level": "INFO",
  "service": "order-worker",
  "event": "order_processed",
  "external_id": "uuid",
  "correlation_id": "uuid",
  "timestamp": "2026-01-01T12:00:00Z"
}
```

## Tasks

* [ ] Configure JSON logging in all services.
* [ ] Generate `X-Correlation-ID` in Core API when absent.
* [ ] Forward `X-Correlation-ID` in all outbound HTTP calls from Core API.
* [ ] Embed `correlation_id` in `OrderCreated` event (already defined in payload).
* [ ] Read `correlation_id` from event in Order Worker.
* [ ] Log Order creation (Order Service).
* [ ] Log event publication (Order Service).
* [ ] Log message consumption start/end (Order Worker).
* [ ] Log processing failures and retries (Order Worker).
* [ ] Log DLQ routing (Order Worker).

## Acceptance Criteria

A single Order creation can be traced from Core API to Order Worker using `correlation_id` in the logs.
No secrets or stack traces in logs.

---

# PHASE 8 — End-to-End Test

## Objective

Validate the complete flow from HTTP request to persisted Order.

## Scenario — Valid Order (happy path)

```text
1. Create Customer     → POST /customers        → 201
2. Create Product      → POST /products         → 201
3. Create Order        → POST /orders           → 202 Accepted
4. Wait Worker         → poll GET /orders/{id}  → status == COMPLETED
5. Verify persistence  → Order and items in PostgreSQL
6. Verify total        → total_amount == sum(quantity * price)
```

## Tests

* [ ] Complete happy path passes.
* [ ] Order with non-existent Customer → Worker sets status FAILED.
* [ ] Order with non-existent Product → Worker sets status FAILED.
* [ ] Order with quantity > stock → Worker sets status FAILED.

## Acceptance Criteria

All E2E test scenarios pass against the running Docker Compose environment.

---

# PHASE 9 — Hardening and Final Documentation

## Code

* [ ] Add missing type hints.
* [ ] Review exception handling consistency.
* [ ] Review input validation coverage.
* [ ] Remove dead code.
* [ ] Run Ruff and Black across all services.
* [ ] Run MyPy across all services.

## Security

* [ ] No secrets in source code.
* [ ] All credentials via environment variables.
* [ ] No stack traces in HTTP responses.
* [ ] No internal details in error responses.

## Database

* [ ] Confirm `UNIQUE(email)` on Customer.
* [ ] Confirm `UNIQUE(external_id)` on Order.
* [ ] Review indexes for common queries.

## Docker

* [ ] Health checks on all services.
* [ ] Restart policies configured.
* [ ] `.env.example` complete and up to date.

## README

* [ ] Project objective.
* [ ] Architecture overview.
* [ ] Technologies.
* [ ] How to run (`docker compose up`).
* [ ] How to run tests.
* [ ] Endpoints.
* [ ] Swagger location.
* [ ] How to scale workers (`--scale order-worker=3`).
* [ ] Known limitations (stock decrement not implemented, Redis idempotency deferred).

## Acceptance Criteria

* [ ] `docker compose up` starts all services.
* [ ] All tests pass.
* [ ] No linting or type errors.
* [ ] README is sufficient to run the project without prior context.

---

# 4. Mandatory Implementation Order

```text
01. Preparation
02. Docker Infrastructure (infra only)
03. Customer Service
04. Product Service
05. Core API
06. Order Service
07. Order Worker
08. Observability
09. End-to-End Test
10. Hardening and Final Documentation
```

Do not change this order without a clear architectural justification.

---

# 5. Definition of Done

A phase may only be considered complete when:

```text
[ ] Code implemented
[ ] Tests implemented and passing
[ ] Acceptance criteria satisfied
[ ] Docker working when applicable
[ ] No regressions in previous phases
[ ] Architecture preserved (Hexagonal, no domain depending on infra)
```

The agent must explicitly report when a phase is complete and list any remaining issues before proceeding.

Do not automatically proceed to the next phase.

---

# 6. Scope Constraints

Do not implement the following unless explicitly requested:

* Kubernetes;
* full authentication;
* payment processing;
* stock decrement on Order completion;
* Redis `NX + TTL` idempotency (deferred — see `docs/decisions.md`);
* `Idempotency-Key` header (deferred — see `docs/decisions.md`);
* Cache Worker;
* Order caching;
* domain events for Customer or Product;
* Outbox Pattern;
* cloud infrastructure;
* service mesh;
* event sourcing.

---

# 7. Known Architectural Decisions (Deferred)

These decisions are intentionally deferred. They are documented here so they are not forgotten.
When implemented, update `docs/decisions.md`.

## Idempotency — Redis Layer

**Current state:** `UNIQUE(external_id)` enforced by PostgreSQL. Duplicate Orders are rejected at persistence time.

**Deferred:** Add `Idempotency-Key` header and Redis `SET NX EX <ttl>` check before publishing to RabbitMQ.
This would prevent duplicate messages from even reaching the Worker, providing an earlier and cheaper rejection.

**Key format when implemented:**
```text
idempotency:{idempotency_key}
```

**Why deferred:** Adds a new port, a new Redis adapter, and middleware in Order Service.
The database constraint already prevents data corruption. The Redis layer is an optimization.

## Stock Decrement

**Current state:** Stock is validated but not decremented when an Order is completed.

**Deferred:** Decrement `Product.stock` in the Order Worker after successful Order persistence.
This requires a decision on concurrency control (optimistic locking or database-level check-and-decrement).

---

# 8. Final Architecture Flow

```text
                        ┌───────────────┐
                        │    CLIENT     │
                        └───────┬───────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │    CORE API     │
                       │ Flask/OpenAPI   │
                       └────────┬────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   Customer Service      Product Service       Order Service
          │                     │                     │
          ▼                     ▼                     ▼
      PostgreSQL            PostgreSQL             RabbitMQ
                                                       │
                                                       ▼
                                              ┌─────────────┐
                                              │Order Worker │
                                              └──────┬──────┘
                                                     │
                         ┌───────────────────────────┼───────────────┐
                         │                           │               │
                         ▼                           ▼               ▼
                       Redis                 Customer Service  Product Service
                         │                           │               │
                         └───────────────────────────┘               │
                                                     │               │
                                                     ▼               │
                                              Order PostgreSQL ◄──────┘
                                          (shared with Order Service)
```

---

# 9. Project Status

```text
[ ] PHASE 0 — Preparation
[ ] PHASE 1 — Docker Infrastructure
[ ] PHASE 2 — Customer Service
[ ] PHASE 3 — Product Service
[ ] PHASE 4 — Core API
[ ] PHASE 5 — Order Service
[ ] PHASE 6 — Order Worker
[ ] PHASE 7 — Observability
[ ] PHASE 8 — End-to-End Test
[ ] PHASE 9 — Hardening and Final Documentation
```

---

# 10. Initial Agent Instruction

Before starting implementation, read completely:

1. `arquitetura_requisitos_projeto.md`
2. `PLAN.md`
3. `AGENTS.md`
4. `docs/conventions.md`
5. `docs/decisions.md`

`PLAN.md` defines the official implementation order.

Implement only one phase at a time.

Before modifying any code:
- identify the current phase;
- inspect the current project state;
- identify existing files;
- identify potential architectural conflicts.

During implementation:
- follow Hexagonal Architecture;
- keep the domain decoupled from infrastructure;
- do not introduce technologies not listed in this plan;
- do not implement future phases;
- write tests for the code being produced in this phase.

After implementation:
1. run the tests;
2. run `ruff check .` and `ruff format .`;
3. verify Docker when applicable;
4. validate the phase acceptance criteria;
5. report the modified files;
6. report any issues found;
7. report whether the phase is complete.

Do not automatically proceed to the next phase.

---

# 11. Architectural Reference

`arquitetura_requisitos_projeto.md` is the primary source for functional requirements,
non-functional requirements, and architectural decisions.

If a conflict exists between this plan and the requirements document, stop implementation
and report the conflict for a decision before changing the architecture.
