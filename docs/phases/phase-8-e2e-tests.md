# PHASE 8 — End-to-End Tests

## Objective

Validate the complete flow from HTTP request to persisted Order against the
running Docker Compose environment.

## Prerequisites

All services must be running:

```bash
docker compose up --build
```

## Scenarios

### Scenario 1 — Happy Path

```text
1. POST /api/v1/customers              → 201  (create Customer)
2. POST /api/v1/products               → 201  (create Product with stock ≥ quantity)
3. POST /api/v1/orders                 → 202  (create Order referencing Customer + Product)
4. Poll GET /api/v1/orders/{external_id} until status == COMPLETED  (max ~5s)
5. Assert total_amount == quantity × product.price
6. Assert OrderItem.unit_price == product.price
```

### Scenario 2 — Non-existent Customer

```text
1. POST /api/v1/orders  with unknown customer_id  → 202
2. Poll GET /api/v1/orders/{external_id}          → status == FAILED
```

### Scenario 3 — Non-existent Product

```text
1. POST /api/v1/customers              → 201
2. POST /api/v1/orders  with unknown product_id   → 202
3. Poll GET /api/v1/orders/{external_id}          → status == FAILED
```

### Scenario 4 — Insufficient Stock

```text
1. POST /api/v1/customers              → 201
2. POST /api/v1/products  with stock=1 → 201
3. POST /api/v1/orders  with quantity=5 → 202
4. Poll GET /api/v1/orders/{external_id} → status == FAILED
```

## Tests

* [ ] Scenario 1 — Happy Path passes.
* [ ] Scenario 2 — Non-existent Customer → FAILED.
* [ ] Scenario 3 — Non-existent Product → FAILED.
* [ ] Scenario 4 — Insufficient Stock → FAILED.

## Acceptance Criteria

* [ ] All 4 scenarios pass against the live Docker Compose environment.
