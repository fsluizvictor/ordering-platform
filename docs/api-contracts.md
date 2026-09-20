# Contratos das APIs

## Convenções

- Base externa: `/api/v1`
- JSON como formato padrão.
- UUID para identificadores.
- Datas em ISO 8601.
- Erros devem possuir formato consistente.
- `Idempotency-Key` é obrigatório para criação de pedidos.
- `external_id` identifica externamente um pedido.

## Customer API

### POST /customers

Cria cliente.

Exemplo:

```json
{
  "name": "João Silva",
  "email": "joao@example.com",
  "phone": "+55 31 99999-9999"
}
```

### GET /customers

Lista clientes.

### GET /customers/{id}

Busca cliente por ID.

### GET /customers/name/{name}

Busca clientes por nome.

### PUT /customers/{id}

Atualiza cliente.

### DELETE /customers/{id}

Remove cliente.

### GET /customers/count

Retorna quantidade de clientes.

## Product API

### POST /products

```json
{
  "name": "Notebook",
  "description": "Notebook para trabalho",
  "price": 3500.00,
  "stock": 10
}
```

### GET /products

Lista produtos.

### GET /products/{id}

Busca produto por ID.

### GET /products/name/{name}

Busca produtos por nome.

### PUT /products/{id}

Atualiza produto.

### DELETE /products/{id}

Remove produto.

### GET /products/count

Retorna quantidade de produtos.

## Order API

### POST /orders

Headers:

```text
Idempotency-Key: <unique-key>
```

Exemplo:

```json
{
  "customer_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 2
    }
  ]
}
```

Resposta:

```http
202 Accepted
```

```json
{
  "external_id": "uuid",
  "status": "PENDING"
}
```

### GET /orders

Lista pedidos.

### GET /orders/{external_id}

Busca pedido.

### GET /orders/count

Retorna quantidade de pedidos.

### PUT /orders/{external_id}

Permitido somente com status `PENDING`. Não altera `external_id` nem `customer_id`.

### DELETE /orders/{external_id}

Permitido em `PENDING` ou `FAILED`. `PROCESSING` e `COMPLETED` retornam 409.

## Evento OrderCreated

Exemplo conceitual:

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

## Erros

Formato recomendado:

```json
{
  "error": {
    "code": "CUSTOMER_NOT_FOUND",
    "message": "Customer not found",
    "request_id": "uuid"
  }
}
```

Códigos HTTP esperados:

- 200 — sucesso de consulta/atualização.
- 201 — criação síncrona.
- 202 — criação assíncrona de pedido.
- 204 — operação sem corpo de resposta.
- 400 — requisição inválida.
- 404 — recurso inexistente.
- 409 — conflito/duplicidade.
- 422 — regra de negócio inválida.
- 500 — erro interno.
