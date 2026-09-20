# PHASE 4 — Core API

## Objective

Create the single public HTTP entry point, proxying Customer and Product services,
with Swagger/OpenAPI documentation.

## Responsibilities

* Route `/api/v1/*` requests to the correct internal service.
* Validate initial request structure.
* Return consistent error responses.
* Generate `X-Request-ID` if absent; propagate `X-Correlation-ID`.
* Structured logging with correlation ID.
* Swagger/OpenAPI at `GET /docs` and `GET /openapi.yaml`.
* Health check at `GET /health`.

## Rules

* No database.
* No business rules.
* Stateless.
* Must not access PostgreSQL or Redis directly.
* Must not publish domain events.

## Routes

All public routes use the `/api/v1` prefix.
Internal services expose resources at the root (no prefix).

```text
Public (Core API)              →   Internal service
/api/v1/customers/**           →   http://customer-service:8001/customers/**
/api/v1/products/**            →   http://product-service:8002/products/**
/api/v1/orders/**              →   http://order-service:8003/orders/**  (wired in Phase 5)
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

* [ ] Request to `/api/v1/customers` is routed to Customer Service.
* [ ] Request to `/api/v1/products` is routed to Product Service.
* [ ] `X-Correlation-ID` is generated when absent.
* [ ] `X-Correlation-ID` is forwarded when present.
* [ ] 4xx from internal service is translated and returned correctly.
* [ ] 5xx from internal service returns safe `INTERNAL_ERROR` response.
* [ ] `GET /health` returns 200.

## Docker

* [ ] Add `core-api` to `docker-compose.yml`.
* [ ] Expose port 8000.
* [ ] Depends on `customer-service` and `product-service` health checks.

## Acceptance Criteria

* [ ] `GET /api/v1/customers` proxied to Customer Service correctly.
* [ ] `GET /api/v1/products` proxied to Product Service correctly.
* [ ] Swagger UI accessible at `http://localhost:8000/docs`.
* [ ] All unit tests pass.
