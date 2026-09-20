# Convenções de implementação

Decisões táticas fechadas para a IA não inventar contratos, nomes ou fluxos.
Regras de negócio continuam em `docs/requirements.md` e `AGENTS.md`.
Este arquivo manda quando houver detalhe operacional em aberto.

Python **3.12**.

Antes de implementar uma fase, ler também `docs/CONTEXT.md` e este documento.

---

## Layout do monorepo

```text
core-api/
customer-service/
product-service/
order-service/
order-worker/
shared/
tests/
docker-compose.yml
```

Cada serviço HTTP segue Hexagonal Architecture:

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

Pacotes Python no `src/` usam o nome do contexto (`customer_service`, `product_service`, `order_service`, `core_api`) para o monorepo não colidir em `domain`.

### Order Service e Order Worker

Mesmo contexto de negócio. **Um código, dois processos.**

- Código hexagonal: `order-service/src/order_service/`
- HTTP: `python -m order_service.main`
- Worker: `python -m order_service.worker`
- `order-worker/` contém apenas Docker (mesmo contexto de build que `order-service`)

Não duplicar entidades Order entre as duas pastas.

### `shared/`

Permitido:

- logging estruturado
- correlation / request ID
- envelope de erro HTTP
- leitura de variáveis de ambiente
- health Flask genérico

Proibido:

- entidades de domínio
- repositórios
- regras de Customer, Product ou Order
- clientes específicos de outro serviço além de helpers HTTP genéricos

---

## Identificadores e tempo

- IDs públicos: UUID v4, string canônica.
- Datas: ISO 8601 UTC (`Z`).
- Base pública: `/api/v1`
- Serviços internos não usam `/api/v1`; expõem o recurso na raiz (`/customers`, `/products`, `/orders`).

---

## Persistência

Um container PostgreSQL, três databases (ownership lógico):

| Serviço | Database |
|---|---|
| Customer Service | `customer_db` |
| Product Service | `product_db` |
| Order Service / Worker | `order_db` |

Nunca consultar o database de outro serviço.

Constraints obrigatórias quando as tabelas existirem:

- `customer.email` UNIQUE
- `order.external_id` UNIQUE

---

## Health

Todos os processos HTTP:

| Path | Significado |
|---|---|
| `GET /health` | Liveness. Não depende de Postgres/Redis/RabbitMQ. |
| `GET /ready` | Readiness. Verifica dependências obrigatórias daquele serviço. |

Order Worker não expõe HTTP. Healthcheck do Compose tenta abrir conexão AMQP.

---

## Core API

- Único Swagger público: `GET /docs` e `GET /openapi.yaml`
- Encaminha `/api/v1/*` aos serviços internos (implementação nas fases seguintes)
- Não contém regras de Customer, Product ou Order
- Gera `X-Request-ID` se ausente; propaga `X-Correlation-ID`

Porta pública: `8000`

Portas internas (Compose):

| Serviço | Porta |
|---|---|
| customer-service | 8001 |
| product-service | 8002 |
| order-service | 8003 |

---

## Erros HTTP

Formato único:

```json
{
  "error": {
    "code": "CUSTOMER_NOT_FOUND",
    "message": "Customer not found",
    "request_id": "uuid"
  }
}
```

Códigos estáveis (usar estes; não criar sinônimos):

| code | HTTP |
|---|---|
| `VALIDATION_ERROR` | 400 |
| `RESOURCE_NOT_FOUND` | 404 |
| `CUSTOMER_NOT_FOUND` | 404 |
| `PRODUCT_NOT_FOUND` | 404 |
| `ORDER_NOT_FOUND` | 404 |
| `EMAIL_ALREADY_EXISTS` | 409 |
| `DUPLICATE_EXTERNAL_ID` | 409 |
| `INSUFFICIENT_STOCK` | 422 |
| `BUSINESS_RULE_VIOLATION` | 422 |
| `INTERNAL_ERROR` | 500 |

> **Futuro:** `IDEMPOTENCY_CONFLICT` (409) e `IDEMPOTENCY_KEY_REQUIRED` (400) serão adicionados
> quando o header `Idempotency-Key` for implementado (ver `docs/decisions.md` — ADR-007).

Não expor stack trace nem SQL.

---

## Customer e Product

CRUD síncrono. Listagens **sem paginação** neste desafio.

Após escrita bem-sucedida no PostgreSQL, invalidar cache Redis (Cache-Aside). O Worker preenche o cache na leitura.

---

## Order — criação

1. Core API valida o contrato da requisição.
2. Order Service gera `external_id`.
3. **Persistir Order `PENDING` no PostgreSQL antes do 202** (permite `GET` imediato).
4. Publicar `OrderCreated`.
5. Responder `202 Accepted`.

O Worker **não** cria o pedido do zero. Ele processa o `PENDING` existente (validações, preços, total, transição de status).

Se a publicação no RabbitMQ falhar depois do insert, a Order permanece `PENDING` e deve ser recuperável (fora do escopo inicial; não usar Outbox).

> **Idempotency-Key deferido.** O header `Idempotency-Key` e a proteção Redis `NX + TTL`
> estão planejados como trabalho futuro. A proteção atual contra duplicatas é
> `UNIQUE(external_id)` no PostgreSQL. Consultar `docs/decisions.md` — ADR-007.

### PUT /orders/{external_id}

Permitido somente com status `PENDING`.
Não altera `external_id`, `customer_id` nem `total_amount` calculado pelo Worker.
Substitui itens ainda não processados.

### DELETE /orders/{external_id}

Permitido em `PENDING` ou `FAILED`.
Negar `PROCESSING` e `COMPLETED` com `409` + `BUSINESS_RULE_VIOLATION`.

---

## Estoque

O Worker **não** acessa o database de Product.

Na fase de processamento, o Product Service deverá expor operação interna de verificação/decremento de estoque. Até lá, não inventar SQL cruzado nem cache como fonte de verdade de stock.

`unit_price` e `total_amount` são definidos no processamento, com o preço do Product naquele momento.

---

## Redis

Não é fonte de verdade. Sem cache de Order.

| Chave | Uso |
|---|---|
| `customer:{id}` | Cache-Aside de Customer |
| `product:{id}` | Cache-Aside de Product |

TTL de cache: `CACHE_TTL_SECONDS` (default 300).

> **Futuro:** `idempotency:{key}` para janela de idempotência HTTP (ver `docs/decisions.md`).

---

## RabbitMQ

| Recurso | Nome |
|---|---|
| Exchange | `orders` (direct, durable) |
| Routing key | `order.created` |
| Fila | `orders.created` |
| DLX | `orders.dlx` |
| DLQ | `orders.created.dlq` |

Uma fila compartilhada por todas as instâncias do Worker. Prefetch configurável (`RABBITMQ_PREFETCH`, default 1). ACK manual somente após commit bem-sucedido.

Retry limitado: `ORDER_MAX_RETRIES` (default 3). Acima disso, DLQ. Sem requeue infinito.

### Payload `OrderCreated`

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

`event_id` identifica o evento; `external_id` identifica o pedido.

---

## Observabilidade

Logs estruturados (JSON em linha). Campos mínimos: `timestamp`, `level`, `service`, `message`, `correlation_id`, `request_id`, `event_id` quando houver.

Nunca logar senhas, URLs com credencial, `Idempotency-Key` completo (truncar se necessário).

---

## Ordem de implementação

Uma sequência só (substitui qualquer lista divergente):

1. Preparation / skeleton / tooling
2. Docker Infrastructure (apenas infra: postgres, redis, rabbitmq)
3. Customer Service
4. Product Service
5. Core API (proxy + OpenAPI)
6. Order Service (HTTP + publicação)
7. Order Worker (consumo + Cache-Aside + Retry/DLQ mínimo)
8. Observabilidade essencial (logging JSON + correlation ID)
9. Testes E2E (happy path completo)
10. Hardening e documentação final

---

## Tooling

Na raiz:

```bash
make lint
make format
make typecheck
make test
```

Não adicionar segundo formatter (Black) nem segundo linter além do Ruff já configurado.
Não adicionar Celery, Kafka, MongoDB, Kubernetes.
