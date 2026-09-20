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
└── Dockerfile
```

## Endpoints

Serviços internos não usam prefixo `/api/v1`.

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
* [ ] Expose port 8001.
* [ ] Depends on `postgres` health check.
* [ ] Add `/ready` health check in Compose.

## Acceptance Criteria

* [ ] Customer Service works independently.
* [ ] All unit tests pass.
* [ ] Service starts and responds via Docker Compose.
* [ ] `GET /health` returns 200; `GET /ready` returns 200 when postgres is up.
