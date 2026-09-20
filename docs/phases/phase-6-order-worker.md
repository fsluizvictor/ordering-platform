# PHASE 6 — Order Worker

## Objective

Implement asynchronous Order processing:
- RabbitMQ consumer with manual ACK.
- Redis Cache-Aside for Customer and Product lookups.
- Business validation, total calculation and persistence.
- Minimal Retry and Dead Letter Queue.

## Processing Flow

```text
RabbitMQ → Order Worker
               │
               ├── Redis GET customer:{id}
               │     ├── HIT  → use cached data
               │     └── MISS → GET /customers/{id} → Redis SET (TTL)
               │
               ├── Redis GET product:{id}  (for each item)
               │     ├── HIT  → use cached data
               │     └── MISS → GET /products/{id} → Redis SET (TTL)
               │
               ├── Validate Customer exists
               ├── Validate all Products exist
               ├── Validate quantity ≤ stock per item
               ├── Calculate total_amount
               ├── Set unit_price per OrderItem
               │
               ├── BEGIN TRANSACTION
               │     UPDATE Order → PROCESSING
               │     INSERT OrderItems
               │     UPDATE Order → COMPLETED
               └── COMMIT → ACK
```

## Retry and DLQ (minimal)

```text
Worker
  ├── success → COMMIT → ACK
  └── failure → retry_count < MAX_RETRIES → NACK (requeue=True)
             └── retry_count ≥ MAX_RETRIES → NACK (requeue=False) → DLQ
```

Implementation:
- `x-dead-letter-exchange` configured at queue declaration (`orders.dlx`).
- Retry counter read from message header `x-retry-count`.
- `MAX_RETRIES` from env var `ORDER_MAX_RETRIES` (default 3).
- NACK with `requeue=False` when limit is exceeded — RabbitMQ routes to DLQ automatically.
- **ACK only after successful COMMIT.**

## RabbitMQ Resources

| Resource | Name |
|---|---|
| Exchange | `orders` (direct, durable) |
| Routing key | `order.created` |
| Queue | `orders.created` |
| Dead-letter exchange | `orders.dlx` |
| DLQ | `orders.created.dlq` |

## Cache Keys

| Key | TTL |
|---|---|
| `customer:{id}` | `CACHE_TTL_SECONDS` (default 300) |
| `product:{id}` | `CACHE_TTL_SECONDS` (default 300) |

Cache invalidation: Customer and Product services invalidate their keys after successful updates.

## Architecture

Order Service and Order Worker share the **same Python package** (`order_service`).
The Worker uses the same Docker image as Order Service with a different entrypoint.

```text
order-service/src/order_service/
├── adapters/
│   ├── inbound/
│   │   ├── http/               ← Order Service HTTP (Phase 5)
│   │   └── messaging/          ← Worker RabbitMQ consumer (this phase)
│   └── outbound/
│       ├── persistence/
│       ├── messaging/          ← publisher (Phase 5)
│       ├── cache/              ← Redis Cache-Aside (this phase)
│       └── external_services/  ← HTTP clients to Customer/Product (this phase)
├── main.py     ← python -m order_service.main
└── worker.py   ← python -m order_service.worker

order-worker/
└── Dockerfile  ← same build context as order-service, different CMD
```

## Tests

### Unit Tests

* [ ] Customer not found → Order status set to FAILED.
* [ ] Product not found → Order status set to FAILED.
* [ ] Quantity exceeds stock → Order status set to FAILED.
* [ ] `total_amount` is calculated correctly from items × prices.
* [ ] `unit_price` is stored per OrderItem.
* [ ] Cache HIT returns cached data without calling external service.
* [ ] Cache MISS calls external service and populates Redis.
* [ ] ACK is sent only after successful COMMIT.
* [ ] NACK is sent when retry limit is exceeded.

### Integration Test — Happy Path

* [ ] Publish a valid `OrderCreated` message to RabbitMQ.
* [ ] Worker processes the message.
* [ ] Order is persisted in PostgreSQL with status `COMPLETED`.
* [ ] OrderItems are persisted with correct `unit_price`.
* [ ] Message is ACKed (queue is empty after processing).

## Docker

* [ ] Add `order-worker` to `docker-compose.yml` using the same build context as `order-service`.
* [ ] `order-worker` Dockerfile CMD: `python -m order_service.worker`.
* [ ] Depends on `postgres`, `redis`, `rabbitmq` health checks.
* [ ] Worker scaling works: `docker compose up --scale order-worker=3`.

## Acceptance Criteria

* [ ] Full async flow end to end: `POST /orders → 202 → RabbitMQ → Worker → PostgreSQL (COMPLETED)`.
* [ ] All unit tests pass.
* [ ] Integration happy path passes.
* [ ] Messages exceeding retry limit are routed to DLQ.
* [ ] `docker compose up --scale order-worker=3` starts 3 Workers consuming the same queue.
