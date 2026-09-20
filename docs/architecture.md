# Arquitetura

## Visão geral

```text
                    ┌─────────────────┐
                    │ External Client │
                    └────────┬────────┘
                             │ HTTP
                             ▼
                    ┌─────────────────┐
                    │    Core API     │
                    │ Entry Point /   │
                    │ Gateway / ACL   │
                    └───┬─────┬───┬───┘
                        │     │   │
              HTTP      │     │   │ HTTP
                        ▼     ▼   ▼
                 Customer  Product Order
                  Service   Service Service
                    │         │       │
                    ▼         ▼       │
               PostgreSQL PostgreSQL  │
                                      │ publish
                                      ▼
                                  RabbitMQ
                                      │
                                      ▼
                                Order Worker
                                  │      │
                         ┌────────┘      └────────┐
                         ▼                       ▼
                       Redis          Customer/Product APIs
                         │
                         ▼
                    PostgreSQL
```

## Componentes

### Core API

Responsável por:

- receber chamadas externas;
- autenticação/autorização quando aplicável;
- validação básica do contrato externo;
- correlation/request ID;
- logging;
- versionamento da API;
- transformação de contratos quando necessário;
- encaminhamento para os serviços internos.

Não possui banco de dados próprio e não deve conter regras de negócio específicas de Customer, Product ou Order.

### Customer Service

Responsável exclusivamente pelo domínio de clientes e seu armazenamento.

### Product Service

Responsável exclusivamente pelo domínio de produtos e seu armazenamento.

### Order Service

Responsável pelo contrato HTTP de pedidos e pela publicação do evento `OrderCreated`.

A criação é assíncrona. O serviço gera o `external_id`, publica o evento e retorna `202 Accepted`.

### Order Worker

Consumidor RabbitMQ responsável pelo processamento de `OrderCreated`.

Durante o processamento:

1. valida a mensagem;
2. consulta Customer no Redis;
3. em cache miss, consulta Customer Service;
4. consulta Product no Redis;
5. em cache miss, consulta Product Service;
6. aplica as regras de pedido;
7. calcula o total;
8. persiste o pedido;
9. confirma a mensagem com ACK.

## Persistência

PostgreSQL é a fonte de verdade.

Conceitualmente:

- Customer Service → Customer DB
- Product Service → Product DB
- Order Service/Worker → Order DB

Um único container PostgreSQL pode hospedar bancos ou schemas separados durante o desafio, mantendo a separação lógica de ownership.

## Cache

Redis utiliza o padrão Cache-Aside.

### Leitura

```text
Consumer → Redis
            │
      ┌─────┴─────┐
      │           │
     HIT         MISS
      │           │
      ▼           ▼
    return   Service API → DB
                         │
                         ▼
                       Redis
```

### Escrita

```text
Service → PostgreSQL → sucesso → DEL Redis
```

O PostgreSQL permanece como fonte de verdade. Redis é descartável.

## Pedido assíncrono

```text
Client
  │
  ▼
Core API
  │
  ▼
Order Service
  │
  ├── gera external_id
  ├── publica OrderCreated
  └── retorna 202
             │
             ▼
          RabbitMQ
             │
             ▼
        Order Worker
             │
             ├── Redis
             ├── Customer/Product APIs em cache miss
             └── Order DB
```

## Idempotência

A requisição de criação deve aceitar `Idempotency-Key`.

Redis pode ser utilizado para controlar a idempotência HTTP com operação atômica equivalente a:

```text
SET key value NX EX <ttl>
```

A proteção definitiva contra duplicidade fica no banco, por meio de uma restrição `UNIQUE` sobre `external_id`.

Isso protege também contra redelivery de mensagens.

## RabbitMQ

O Order Worker deve usar:

- manual ACK;
- prefetch limitado;
- retry limitado;
- Dead Letter Queue;
- mensagens não confirmadas permanecendo disponíveis para redelivery.

Múltiplas instâncias do Order Worker podem consumir a mesma fila.

## Escalabilidade

Customer, Product, Order e principalmente Order Worker devem poder ser escalados horizontalmente.

Exemplo:

```bash
docker compose up --scale order-worker=3
```

## Restrições arquiteturais

- Não colocar regras de negócio no Core API.
- Não acessar diretamente o banco de outro serviço.
- Não compartilhar entidades de domínio entre serviços.
- Não utilizar Redis como fonte de verdade.
- Não criar cache para Order sem decisão arquitetural explícita.
- Não processar a criação do pedido de forma síncrona no HTTP.
- Não substituir RabbitMQ por chamadas HTTP para o fluxo assíncrono.
