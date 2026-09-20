# PHASE 5 — Order Service

## Objective

Implement the Order domain and HTTP entry point.
At the end of this phase, `POST /orders` persists a `PENDING` Order and publishes
`OrderCreated` to RabbitMQ, returning `202 Accepted`.

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
* [ ] `external_id` must be unique — enforced by `UNIQUE` constraint in PostgreSQL.
* [ ] Status transitions: `PENDING → PROCESSING → COMPLETED | FAILED`.
* [ ] `total_amount` is calculated at Worker processing time.
* [ ] `unit_price` stores the price at processing time (set by the Worker, not the Service).

## POST /orders — Creation Sequence

```text
1. Validate request payload.
2. Generate external_id (UUID v4).
3. Persist Order as PENDING in PostgreSQL  ← enables immediate GET /orders/{external_id}
4. Publish OrderCreated to RabbitMQ.
5. Return 202 Accepted.
```

The Worker processes the existing `PENDING` record — it does not create the Order from scratch.

If RabbitMQ publish fails after the INSERT, the Order remains `PENDING` and can be recovered.
No Outbox Pattern at this stage.

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
    { "product_id": "uuid", "quantity": 2 }
  ]
}
```

## HTTP Endpoints

```http
POST   /orders              → persist PENDING + publish OrderCreated → 202 Accepted
GET    /orders              → list Orders
GET    /orders/{external_id}
GET    /orders/count
PUT    /orders/{external_id}    → only allowed when status is PENDING
DELETE /orders/{external_id}    → only allowed when status is PENDING or FAILED
```

## Response for POST /orders

```http
HTTP 202 Accepted
```
```json
{ "external_id": "uuid", "status": "PENDING" }
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
│   │   │   ├── http/           ← HTTP routes (this phase)
│   │   │   └── messaging/      ← Worker consumer (Phase 6)
│   │   └── outbound/
│   │       ├── persistence/
│   │       ├── messaging/      ← RabbitMQ publisher
│   │       ├── cache/          ← Redis (Phase 6)
│   │       └── external_services/ ← HTTP clients (Phase 6)
│   ├── config/
│   ├── main.py                 ← HTTP entrypoint
│   └── worker.py               ← Worker entrypoint (Phase 6)
├── tests/
│   ├── unit/
│   └── integration/
└── Dockerfile
```

> Order Service and Order Worker share the same `order_db` PostgreSQL database.
> Order Service reads. Order Worker writes (status transitions, OrderItems).

## Tests

### Unit Tests

* [ ] Order with no items is rejected.
* [ ] Item with quantity zero is rejected.
* [ ] Valid status transitions are enforced.
* [ ] `external_id` is generated on creation.
* [ ] `event_id` and `occurred_at` are set on the event.
* [ ] `correlation_id` is propagated to the event.
* [ ] HTTP 202 returned on valid creation request.
* [ ] HTTP 422 returned on invalid request.

### Integration Test — Happy Path

* [ ] `POST /orders` with valid payload returns 202.
* [ ] `OrderCreated` message is present in the RabbitMQ queue.
* [ ] `GET /orders/{external_id}` returns the Order with status `PENDING`.

## Docker

* [ ] Add `order-service` to `docker-compose.yml`.
* [ ] Expose port 8003.
* [ ] Depends on `postgres` and `rabbitmq` health checks.
* [ ] Wire Core API `/api/v1/orders` → `order-service:8003/orders`.

## Acceptance Criteria

* [ ] `POST /orders` returns `202 Accepted` with `external_id`.
* [ ] `OrderCreated` is published to RabbitMQ.
* [ ] `GET /orders/{external_id}` works immediately after creation.
* [ ] All unit tests pass.
* [ ] Integration happy path passes.
