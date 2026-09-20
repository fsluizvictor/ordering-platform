# Decisões Arquiteturais

## ADR-001 — Core API como ponto de entrada

### Decisão

Todas as chamadas externas entram pelo Core API.

### Motivo

Centralizar preocupações transversais e evitar exposição direta dos serviços internos.

### Consequência

Os serviços de domínio permanecem independentes do contrato externo quando houver necessidade de transformação.

---

## ADR-002 — Customer e Product síncronos

### Decisão

Operações de Customer e Product serão processadas de forma síncrona.

### Motivo

CRUD simples não exige processamento assíncrono neste escopo.

---

## ADR-003 — Criação de Order assíncrona

### Decisão

`POST /orders` publica `OrderCreated` no RabbitMQ e retorna `202 Accepted`.

### Motivo

Separar o recebimento do pedido do processamento e permitir escala independente do worker.

---

## ADR-004 — RabbitMQ

### Decisão

RabbitMQ será o broker do fluxo de pedidos.

### Motivo

O problema exige uma fila de trabalho com ACK, redelivery, retry e DLQ. Não há necessidade, neste escopo, de uma plataforma de event streaming.

---

## ADR-005 — Redis apenas para Customer e Product

### Decisão

Redis será utilizado como cache de Customer e Product.

### Motivo

O Order Worker precisa consultar esses dados rapidamente.

### Consequência

Redis não é fonte de verdade e Order não terá cache neste escopo inicial.

---

## ADR-006 — Cache-Aside

### Decisão

Leituras consultarão Redis primeiro. Em cache miss, o serviço de origem será consultado e o resultado será armazenado no Redis.

### Escrita

A persistência ocorre primeiro no PostgreSQL e, após sucesso, o cache é invalidado.

---

## ADR-007 — Idempotência

### Decisão atual

Usar `UNIQUE(external_id)` no banco de dados como proteção contra duplicatas de Order.
O banco rejeita qualquer tentativa de persistir dois pedidos com o mesmo `external_id`.

### Motivo

Suficiente para garantir integridade dos dados nesta fase sem adicionar complexidade ao
Order Service (nova port, adapter Redis, middleware HTTP).

### Decisão futura (deferida)

Adicionar `Idempotency-Key` header e proteção Redis `SET NX EX <TTL>` como camada
anterior ao processamento, evitando que mensagens duplicadas cheguem ao Worker.

Chave Redis: `idempotency:{idempotency_key}` com TTL `IDEMPOTENCY_TTL_SECONDS` (default 86400).
Implementar quando explicitamente solicitado. Atualizar este ADR ao implementar.

---

## ADR-008 — PostgreSQL como fonte de verdade

### Decisão

Todos os dados persistidos devem possuir PostgreSQL como fonte de verdade.

### Consequência

Falhas ou perda do Redis não podem causar perda de dados de negócio.

---

## ADR-009 — Hexagonal Architecture

### Decisão

Customer, Product e Order utilizarão separação entre domínio, aplicação e adapters.

### Objetivo

Reduzir acoplamento entre regras de negócio e frameworks, banco, HTTP e mensageria.

---

## ADR-010 — Docker Compose

### Decisão

O ambiente local será executado com Docker Compose.

### Motivo

Facilitar inicialização, integração entre componentes e reprodução do ambiente.

---

## ADR-011 — Order PENDING persistido no HTTP

### Decisão

`POST /orders` grava a Order como `PENDING` no PostgreSQL antes de retornar `202`.

### Motivo

Permitir `GET /orders/{external_id}` imediatamente e dar ao Worker um registro para transicionar, em vez de criar o pedido só no consumo.

---

## ADR-012 — Order Worker reutiliza o código do Order Service

### Decisão

Order Service e Order Worker são processos distintos e o mesmo contexto de domínio. O código vive em `order-service/`; o Worker usa a mesma imagem com outro entrypoint.

### Motivo

Evitar duplicar entidades e regras de Order entre dois diretórios.

---

## ADR-013 — Um PostgreSQL, três databases

### Decisão

O Compose sobe um container PostgreSQL com `customer_db`, `product_db` e `order_db`.

### Motivo

Separação lógica de ownership sem três instâncias no desafio. Continua proibido acessar o database de outro serviço.
