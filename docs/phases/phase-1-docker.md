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
* [ ] Configure PostgreSQL (databases: `customer_db`, `product_db`, `order_db`; credentials via env vars).
* [ ] Configure Redis.
* [ ] Configure RabbitMQ (management plugin enabled, credentials via env vars).
* [ ] Configure named volumes for postgres and redis data.
* [ ] Configure a shared network for all services.
* [ ] Configure health checks for postgres, redis, rabbitmq.
* [ ] Complete `.env.example` with all infrastructure variables.

## Acceptance Criteria

Run:

```bash
docker compose up postgres redis rabbitmq
```

All three infrastructure containers must start and report healthy.

```bash
docker compose ps
```

All three must show `healthy` or `running` status.
