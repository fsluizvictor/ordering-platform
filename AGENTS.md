# AGENTS.md

## 1. Project Overview

This repository contains a distributed online sales platform.

Business domains:
- Customer
- Product
- Order

Services:
1. Core API
2. Customer Service
3. Product Service
4. Order Service
5. Order Worker

Priorities:
- correctness
- simplicity
- maintainability
- testability
- scalability

Do not introduce unnecessary complexity.

## 2. Mandatory Stack

Use:
- Python
- Flask
- SQLAlchemy
- PostgreSQL
- Redis
- RabbitMQ
- Pika
- Docker
- Docker Compose
- OpenAPI / Swagger
- Pytest

Do not introduce new infrastructure or frameworks without justification and explicit approval.

Do not introduce Kubernetes, Kafka, Celery, MongoDB, Elasticsearch, GraphQL, Event Sourcing, CQRS, or Outbox Pattern unless explicitly requested.

## 3. Architecture

Use Hexagonal Architecture.

Expected structure:

```text
src/
├── domain/
│   ├── entities/
│   └── ports/
├── application/
│   └── services/
├── adapters/
│   ├── inbound/
│   └── outbound/
├── config/
└── main.py
```

Dependency direction:

```text
Adapters -> Application -> Domain
```

Domain must not directly depend on Flask, SQLAlchemy, PostgreSQL, Redis, RabbitMQ, or Pika.

Infrastructure must be accessed through ports/interfaces.

## 4. Services

### Core API

The only public HTTP entry point.

Responsibilities:
- routing
- request validation
- Swagger/OpenAPI
- error handling
- logging
- correlation ID
- communication with internal services
- contract translation when necessary

It is stateless and has no business database.

Do not place Customer, Product, or Order business rules here.

### Customer Service

Owns Customer:
- CRUD
- find all
- find by ID
- find by name
- count
- business rules
- PostgreSQL persistence

### Product Service

Owns Product:
- CRUD
- find all
- find by ID
- find by name
- count
- business rules
- PostgreSQL persistence
- basic stock validation

### Order Service

Owns the HTTP side of Order:
- receive Order creation
- validate request
- generate `external_id`
- publish `OrderCreated`
- return `202 Accepted`
- query/update/delete Orders

It must not perform the complete asynchronous Order processing.

### Order Worker

Owns asynchronous Order processing:
- consume RabbitMQ
- process `OrderCreated`
- validate Customer/Product
- use Redis cache
- fallback to Customer/Product Services on cache miss
- apply business rules
- persist Order
- enforce idempotency
- ACK successful messages
- retry failures
- send exhausted messages to DLQ

Order Service and Order Worker belong to the same business context but are separate processes/containers. They may share Domain/Application concepts.

## 5. Domain Model

### Customer

```text
Customer
├── id: UUID
├── name: string
├── email: string
├── phone: string
├── created_at: datetime
└── updated_at: datetime
```

Rules:
- name required
- email required
- email unique

### Product

```text
Product
├── id: UUID
├── name: string
├── description: string
├── price: decimal
├── stock: integer
├── created_at: datetime
└── updated_at: datetime
```

Rules:
- name required
- price > 0
- stock >= 0

### Order

```text
Order
├── id: UUID
├── external_id: UUID
├── customer_id: UUID
├── status
├── total_amount: decimal
├── created_at: datetime
└── updated_at: datetime
```

### OrderItem

```text
OrderItem
├── id: UUID
├── order_id: UUID
├── product_id: UUID
├── quantity: integer
└── unit_price: decimal
```

Relationship:

```text
Customer 1 ─── N Order 1 ─── N OrderItem N ─── 1 Product
```

## 6. Order Rules

- Order must contain at least one item.
- Quantity must be greater than zero.
- Customer must exist.
- Products must exist.
- Requested quantity cannot exceed stock.
- Total is calculated by the system.
- `unit_price` stores the price at order processing time.
- `external_id` is unique.
- Creation is idempotent.

Statuses:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

## 7. REST API

Customer:

```text
POST   /customers
GET    /customers
GET    /customers/{id}
GET    /customers/name/{name}
PUT    /customers/{id}
DELETE /customers/{id}
GET    /customers/count
```

Product:

```text
POST   /products
GET    /products
GET    /products/{id}
GET    /products/name/{name}
PUT    /products/{id}
DELETE /products/{id}
GET    /products/count
```

Order:

```text
POST   /orders
GET    /orders
GET    /orders/{external_id}
GET    /orders/count
PUT    /orders/{external_id}
DELETE /orders/{external_id}
```

Order creation returns:

```http
202 Accepted
```

Example:

```json
{
  "external_id": "uuid",
  "status": "PENDING"
}
```

## 8. Order Flow

```text
Client
  ↓
Core API
  ↓
Order Service
  ↓
RabbitMQ
  ↓
Order Worker
  ↓
Redis
  ↓
Customer/Product Service on cache miss
  ↓
PostgreSQL
```

Generate `external_id` before publishing.

`OrderCreated` must contain `event_id`.

Example:

```json
{
  "event_id": "uuid",
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

## 9. Redis

Redis has two responsibilities:
1. Customer/Product cache.
2. Idempotency.

Redis is not the source of truth.

Use Cache-Aside.

Read:
- cache hit -> return data
- cache miss -> call service -> populate Redis -> return data

Write:
- persist to PostgreSQL
- invalidate Redis key

Do not create a Cache Worker.

## 10. Idempotency

Use the `Idempotency-Key` header.

Use an atomic Redis operation equivalent to:

```python
redis.set(key, value, nx=True, ex=TTL)
```

Do not use a separate `exists` followed by `set`, because it is subject to race conditions.

Key convention:

```text
idempotency:{idempotency_key}
```

PostgreSQL must also enforce:

```text
UNIQUE(external_id)
```

Redis protects the idempotency window; PostgreSQL provides the final persistence-level protection.

## 11. RabbitMQ

RabbitMQ is a work queue for asynchronous Orders.

All Order Workers consume the same queue:

```text
RabbitMQ Queue
├── Worker 1
├── Worker 2
└── Worker 3
```

Do not create one queue per Worker.

Use manual ACK.

ACK only after:
1. Customer validation
2. Product validation
3. business validation
4. persistence
5. successful commit

If a Worker fails before ACK, redelivery is expected. The Worker must be idempotent.

## 12. Retry and DLQ

Use bounded retries.

Never create infinite requeue loops.

After the retry limit, send the message to a Dead Letter Queue.

Retry limits must be configurable.

## 13. PostgreSQL

PostgreSQL is the source of truth.

Use database constraints for important integrity rules, including:

```text
Customer.email UNIQUE
Order.external_id UNIQUE
```

Do not rely only on Python validation for database integrity.

## 14. Docker

Docker Compose must run:

```text
core-api
customer-service
product-service
order-service
order-worker
postgres
redis
rabbitmq
```

The environment must work with:

```bash
docker compose up
```

Horizontal Worker scaling must work with:

```bash
docker compose up --scale order-worker=3
```

Do not assume Kubernetes.

## 15. Configuration

Never hardcode credentials or secrets.

Use environment variables.

Provide:

```text
.env.example
```

Never commit:

```text
.env
```

## 16. Testing

Use Pytest.

Structure:

```text
tests/
├── unit/
└── integration/
```

Important scenarios:
- Customer CRUD
- duplicate Customer email
- Product CRUD
- invalid price/stock
- Order creation
- nonexistent Customer
- nonexistent Product
- insufficient stock
- total calculation
- idempotency
- duplicate external_id
- Worker processing
- RabbitMQ redelivery
- retry
- DLQ

## 17. Observability

Implement:
- logging
- correlation ID
- request ID
- event ID

Propagate correlation IDs between services when possible.

Logs must allow tracing:

```text
Client
  ↓
Core API
  ↓
Order Service
  ↓
RabbitMQ
  ↓
Order Worker
```

Never log secrets or sensitive credentials.

## 18. Error Handling

Use consistent API errors, for example:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Customer not found",
    "request_id": "uuid"
  }
}
```

Do not expose stack traces or internal implementation details.

Use appropriate HTTP status codes.

## 19. Swagger

Only Core API exposes public Swagger/OpenAPI documentation.

Document:
- endpoints
- parameters
- headers
- request bodies
- responses
- status codes
- schemas
- examples

Document `Idempotency-Key` on `POST /orders` and the `202 Accepted` response.

## 20. Coding Standards

Prefer:
- clear names
- small functions
- single responsibility
- dependency inversion
- composition
- type hints
- explicit ports/interfaces
- readable control flow
- testable business logic

Avoid:
- premature abstractions
- unnecessary design patterns
- generic repositories without need
- giant classes
- giant functions
- business logic in controllers
- SQL scattered through the application
- direct infrastructure calls from Domain

Favor readable code over clever code.

## 21. Shared Code

Keep `shared/` minimal.

Do not share domain entities, repositories, or business rules between services without a strong architectural reason.

Do not turn `shared/` into a hidden monolith.

Shared code should preferably contain only truly cross-cutting utilities such as logging or generic configuration helpers.

When uncertain, keep code inside the owning service.

## 22. Development Order

Implement incrementally:

1. repository/service structure
2. Docker Compose
3. PostgreSQL
4. Customer Service
5. Product Service
6. Core API
7. Order Service
8. RabbitMQ
9. Order Worker
10. Redis Cache-Aside
11. Idempotency
12. Retry/DLQ
13. Swagger/OpenAPI
14. tests
15. observability
16. documentation

Each phase should leave the project runnable.

## 23. AI Agent Rules

Before changing code:
1. Inspect the repository.
2. Understand the affected service.
3. Identify the architectural layer.
4. Read relevant files under `docs/`.
5. Check existing tests.
6. Reuse existing abstractions when appropriate.
7. Avoid unrelated changes.

For every implementation task:
1. Briefly explain the plan.
2. Identify files to create/modify.
3. Implement only the requested scope.
4. Run relevant tests or validation.
5. Report failures clearly.
6. Do not silently change architecture.
7. Do not introduce new dependencies without justification.

If requirements are ambiguous, prefer the simplest interpretation consistent with this document. Ask for clarification when ambiguity affects architecture, data integrity, API contracts, or business rules.

Do not guess critical requirements.

## 24. Architectural Guardrails

These decisions are fixed unless explicitly changed:

- Python
- Flask
- PostgreSQL
- Redis
- RabbitMQ
- Pika
- Docker Compose
- Hexagonal Architecture
- Core API as public entry point
- Customer Service synchronous
- Product Service synchronous
- Order creation asynchronous
- Order Worker
- Cache-Aside
- Redis for idempotency
- PostgreSQL UNIQUE `external_id`
- manual RabbitMQ ACK
- bounded retry
- DLQ
- horizontal Order Worker scaling
- Swagger only on Core API

If a requested implementation conflicts with these decisions, do not silently override them. Explain the conflict first.

## 25. Architecture Changes

When changing an architectural decision:

1. Explain why the current decision is insufficient.
2. Describe the impact.
3. Update `docs/decisions.md`.
4. Update architecture documentation.
5. Update tests.
6. Update Docker/configuration if necessary.
7. Then implement the change.

Architecture changes must be intentional and documented.

## 26. Main Principle

This is primarily an architecture exercise.

Prioritize:

```text
Correctness
    >
Simplicity
    >
Maintainability
    >
Testability
    >
Scalability
```

Do not introduce complexity merely to demonstrate knowledge.

Every component must have a clear responsibility.

When two solutions satisfy the requirements, prefer the simpler one.
