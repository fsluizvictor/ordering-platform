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

Same hexagonal structure as Customer Service, scoped to `product_service` package.

```text
product-service/
├── src/product_service/
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
└── Dockerfile
```

## Endpoints

Serviços internos não usam prefixo `/api/v1`.

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
* [ ] Expose port 8002.
* [ ] Depends on `postgres` health check.
* [ ] Add `/ready` health check in Compose.

## Acceptance Criteria

* [ ] Product Service works independently.
* [ ] All unit tests pass.
* [ ] Service starts and responds via Docker Compose.
* [ ] `GET /health` returns 200; `GET /ready` returns 200 when postgres is up.
