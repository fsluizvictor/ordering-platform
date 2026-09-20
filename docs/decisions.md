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

### Decisão

Usar `Idempotency-Key` para criação de pedidos e `UNIQUE(external_id)` no banco.

### Motivo

Proteger tanto contra requisições HTTP duplicadas quanto contra redelivery de mensagens.

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
