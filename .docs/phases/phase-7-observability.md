# PHASE 7 — Observability (essential only)

## Objective

Enable traceability across the full request and async processing flow.
Scope: structured JSON logging and correlation ID propagation. Nothing more.

> The infrastructure for this phase is mostly already in `shared/` (JsonFormatter,
> ServiceFilter, setup_logging, init_correlation). This phase ensures all services
> call it correctly and propagate the IDs end to end.

## Correlation ID Flow

```text
Client
  ↓  (Core API generates X-Correlation-ID if absent)
Core API
  ↓  (forwards X-Correlation-ID in outbound HTTP calls)
Order Service
  ↓  (embeds correlation_id in OrderCreated event payload)
RabbitMQ
  ↓  (Worker reads correlation_id from event)
Order Worker
```

Header: `X-Correlation-ID`

## Log Format

```json
{
  "timestamp": "2026-01-01T12:00:00Z",
  "level": "INFO",
  "service": "order-worker",
  "message": "order processed",
  "correlation_id": "uuid",
  "external_id": "uuid"
}
```

Fields `event_id` and `request_id` included when available. No secrets, no stack traces.

## Tasks

* [ ] Confirm `setup_logging(SERVICE_NAME, log_level())` is called in all service entrypoints.
* [ ] Confirm `init_correlation(app)` is called in all Flask apps.
* [ ] Core API forwards `X-Correlation-ID` in all outbound proxy requests.
* [ ] `correlation_id` is embedded in `OrderCreated` event (already in payload spec).
* [ ] Worker reads `correlation_id` from event and includes it in log records.
* [ ] Log Order creation start/end (Order Service).
* [ ] Log event publication (Order Service).
* [ ] Log message consumption start/end (Order Worker).
* [ ] Log validation failures (Order Worker).
* [ ] Log retry attempts and DLQ routing (Order Worker).

## Acceptance Criteria

* [ ] A single Order creation can be traced from Core API to Order Worker using `correlation_id` in logs.
* [ ] No secrets, credentials, or stack traces appear in any log output.
