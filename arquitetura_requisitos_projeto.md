# Documento de Requisitos e Arquitetura — Plataforma de Vendas Online

## 1. Visão geral

Este projeto consiste na construção de uma plataforma distribuída para uma grande empresa de vendas on-line. O sistema deverá disponibilizar dados de **clientes, produtos e pedidos** para consumidores e parceiros por meio de APIs REST.

O desafio original solicita uma API RESTful com operações CRUD, contagem, consulta de todos os registros, consulta por ID e consulta por nome, além da documentação da arquitetura e da organização do código. A persistência de dados é opcional no enunciado, mas é considerada um diferencial. 

> Fonte do desafio: *Enunciado do Desafio Final — Arquiteto(a) de Software*.

A solução proposta amplia esses requisitos com uma arquitetura de microsserviços, processamento assíncrono de pedidos, cache, mensageria, idempotência e persistência.

---

# 2. Cenário de negócio

A empresa possui três principais domínios de negócio:

- **Customer** — gerenciamento de clientes;
- **Product** — gerenciamento de produtos;
- **Order** — criação e consulta de pedidos.

A plataforma será utilizada por clientes e parceiros externos. A **Core API** será o único ponto de entrada HTTP público, sendo responsável por receber as requisições externas e encaminhá-las aos serviços internos.

Os serviços de Customer e Product trabalharão de forma síncrona. A criação de pedidos será assíncrona para permitir que o recebimento da solicitação seja desacoplado do processamento completo do pedido.

### Fluxo de criação de pedido

```text
Cliente
   |
   v
Core API
   |
   v
Order Service
   |
   v
RabbitMQ
   |
   v
Order Worker
   |
   +----> Redis
   |        |
   |        +----> Customer Service (cache miss)
   |        |
   |        +----> Product Service  (cache miss)
   |
   v
Order PostgreSQL
```

Ao receber uma solicitação de criação de pedido:

1. A Core API recebe e valida a requisição.
2. A requisição é encaminhada ao Order Service.
3. O Order Service gera o identificador externo do pedido.
4. O pedido é publicado no RabbitMQ.
5. A API retorna `202 Accepted`.
6. Um ou mais Order Workers consomem as mensagens.
7. O Worker valida Customer e Product.
8. O Worker utiliza Redis como cache para essas consultas.
9. Em caso de cache miss, consulta os serviços de Customer/Product.
10. O pedido é persistido no PostgreSQL.
11. Após o processamento bem-sucedido, a mensagem é confirmada com ACK.
12. Em caso de falha, a mensagem poderá ser reprocessada e, após as tentativas configuradas, enviada para uma Dead Letter Queue.

---

# 3. Objetivos técnicos

A solução deverá demonstrar:

- API REST;
- arquitetura baseada em microsserviços;
- Hexagonal Architecture;
- separação de responsabilidades;
- persistência relacional;
- cache;
- mensageria assíncrona;
- processamento concorrente;
- escalabilidade horizontal do Worker;
- idempotência;
- tratamento de falhas e retries;
- documentação OpenAPI/Swagger;
- execução reproduzível por Docker Compose;
- testes automatizados.

O desafio original recomenda a organização de responsabilidades entre Controller, Model e Service e solicita documentação da estrutura e dos componentes. A arquitetura hexagonal será utilizada como evolução dessa separação, mantendo as responsabilidades isoladas. 

---

# 4. Arquitetura da solução

## 4.1 Microsserviços

A solução será composta por cinco microsserviços:

1. **Core API**
2. **Customer Service**
3. **Product Service**
4. **Order Service**
5. **Order Worker**

### Core API

Responsabilidades:

- ponto de entrada público;
- documentação Swagger/OpenAPI;
- autenticação/autorização, caso implementada;
- validação inicial;
- roteamento;
- tratamento de erros;
- logging e correlation ID;
- comunicação HTTP com os serviços internos.

A Core API será stateless e não possuirá banco de dados próprio.

### Customer Service

Responsável pelo domínio de clientes:

- CRUD de Customer;
- consultas;
- validações de negócio;
- persistência de Customer.

### Product Service

Responsável pelo domínio de produtos:

- CRUD de Product;
- consultas;
- validações de negócio;
- persistência de Product;
- controle básico de estoque.

### Order Service

Responsável pela entrada e consulta de pedidos:

- receber requisições de criação;
- gerar `external_id`;
- validar a requisição;
- publicar `OrderCreated`;
- consultar pedidos persistidos;
- atualizar ou excluir pedidos conforme as regras definidas.

O processamento completo da criação será realizado pelo Order Worker.

### Order Worker

Responsável pelo processamento assíncrono:

- consumir eventos do RabbitMQ;
- validar Customer;
- validar Product;
- consultar Redis;
- consultar Customer/Product Service em caso de cache miss;
- aplicar regras de negócio;
- persistir o pedido;
- controlar idempotência;
- realizar ACK somente após processamento bem-sucedido;
- participar da estratégia de retry/DLQ.

É possível executar múltiplas instâncias do Order Worker para escala horizontal.

---

# 5. Arquitetura hexagonal

Cada serviço deverá separar o núcleo de negócio das tecnologias externas.

Estrutura conceitual:

```text
Domain
  |
  v
Application
  |
  +---- Inbound Adapters
  |
  +---- Outbound Adapters
```

Exemplo:

```text
order-service/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   └── ports/
│   ├── application/
│   │   └── services/
│   ├── adapters/
│   │   ├── inbound/
│   │   │   └── http/
│   │   └── outbound/
│   │       ├── persistence/
│   │       ├── messaging/
│   │       └── external_services/
│   └── main.py
└── tests/
```

O **Order Service** e o **Order Worker** pertencem ao mesmo contexto de negócio e poderão compartilhar domínio e casos de uso, porém serão processos/containerizados independentes. A principal diferença será o adaptador de entrada:

- Order Service → HTTP;
- Order Worker → RabbitMQ.

---

# 6. Tecnologias

| Tecnologia | Responsabilidade |
|---|---|
| Python | Linguagem |
| Flask | APIs REST |
| SQLAlchemy | Persistência/ORM |
| PostgreSQL | Banco de dados relacional |
| Redis | Cache e idempotência |
| RabbitMQ | Mensageria |
| Pika | Cliente RabbitMQ para Python |
| OpenAPI/Swagger | Documentação da Core API |
| Pytest | Testes automatizados |
| Docker | Containerização |
| Docker Compose | Orquestração do ambiente local |

Não será utilizado Kubernetes neste primeiro momento, pois o objetivo é manter a implementação simples e suficiente para demonstrar os requisitos arquiteturais.

---

# 7. Domínios e entidades

## 7.1 Customer

```text
Customer
├── id
├── name
├── email
├── phone
├── created_at
└── updated_at
```

Regras:

- `name` é obrigatório;
- `email` é obrigatório;
- `email` deve ser único.

## 7.2 Product

```text
Product
├── id
├── name
├── description
├── price
├── stock
├── created_at
└── updated_at
```

Regras:

- `name` é obrigatório;
- `price > 0`;
- `stock >= 0`.

## 7.3 Order

```text
Order
├── id
├── external_id
├── customer_id
├── status
├── total_amount
├── created_at
└── updated_at
```

## 7.4 OrderItem

```text
OrderItem
├── id
├── order_id
├── product_id
├── quantity
└── unit_price
```

Relação:

```text
Customer 1 ─── N Order 1 ─── N OrderItem N ─── 1 Product
```

---

# 8. Regras de negócio

## Customer

- Nome não pode ser vazio.
- E-mail é obrigatório.
- E-mail deve ser único.

## Product

- Nome não pode ser vazio.
- Preço deve ser maior que zero.
- Estoque não pode ser negativo.

## Order

- Uma Order deve possuir pelo menos um item.
- A quantidade de cada item deve ser maior que zero.
- O Customer informado deve existir.
- Todos os Products informados devem existir.
- A quantidade solicitada não pode ser maior que o estoque disponível.
- O total da Order deve ser calculado pelo sistema.
- O preço utilizado no pedido deve ser armazenado em `OrderItem.unit_price`.
- `external_id` deve ser único.
- A mesma requisição não deve criar duas Orders.
- O processamento deve respeitar os estados da Order.

Estados:

```text
PENDING
   |
   v
PROCESSING
   |
   +----> COMPLETED
   |
   +----> FAILED
```

---

# 9. Cache

Redis será utilizado exclusivamente como cache para Customer e Product.

Será utilizado o padrão **Cache-Aside**.

### Leitura

```text
Worker
  |
  v
Redis
  |
  +-- HIT --> retorna dados
  |
  +-- MISS --> Customer/Product Service
                    |
                    v
                  Redis
```

### Escrita

Customer/Product Service:

```text
Atualiza PostgreSQL
       |
       v
Invalida chave Redis
```

O PostgreSQL permanece como fonte de verdade.

Não será criado um Cache Worker, pois isso adicionaria complexidade sem necessidade para o cenário.

---

# 10. Mensageria

RabbitMQ será utilizado para o processamento assíncrono de Orders.

Evento principal:

```text
OrderCreated
```

Exemplo conceitual:

```json
{
  "event_id": "uuid",
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

A fila será compartilhada por múltiplas instâncias do Order Worker.

```text
                    ┌── Worker 1
                    |
RabbitMQ Queue ─────┼── Worker 2
                    |
                    └── Worker 3
```

Isso permite escala horizontal do processamento.

---

# 11. Idempotência

A idempotência será implementada em duas camadas.

## Redis

A requisição utilizará:

```http
Idempotency-Key: <unique-key>
```

A chave será armazenada no Redis utilizando operação atômica com `NX` e TTL.

Conceitualmente:

```text
idempotency:{key}
```

O TTL limita o período em que a chave permanece armazenada.

## PostgreSQL

A tabela Order terá:

```text
UNIQUE(external_id)
```

O Redis evita processamento desnecessário e o banco representa a proteção definitiva contra persistência duplicada.

---

# 12. ACK, retry e Dead Letter Queue

O Worker deverá utilizar ACK manual.

Fluxo de sucesso:

```text
RabbitMQ
   |
   v
Worker
   |
   v
Processa
   |
   v
COMMIT PostgreSQL
   |
   v
ACK
```

Se o Worker falhar antes do ACK, a mensagem poderá ser entregue novamente.

A aplicação deverá ser idempotente para suportar esse comportamento.

Em caso de falhas recuperáveis, a mensagem poderá ser submetida a retry. Após o limite de tentativas definido, a mensagem deverá ser encaminhada para uma **Dead Letter Queue (DLQ)**.

---

# 13. API REST

A Core API será o ponto de entrada público.

Os recursos principais serão:

```text
/customers
/products
/orders
```

Operações esperadas:

### Customer

```text
POST   /customers
GET    /customers
GET    /customers/{id}
GET    /customers/name/{name}
PUT    /customers/{id}
DELETE /customers/{id}
GET    /customers/count
```

### Product

```text
POST   /products
GET    /products
GET    /products/{id}
GET    /products/name/{name}
PUT    /products/{id}
DELETE /products/{id}
GET    /products/count
```

### Order

```text
POST   /orders
GET    /orders
GET    /orders/{external_id}
GET    /orders/count
PUT    /orders/{external_id}
DELETE /orders/{external_id}
```

A criação de Order deverá retornar:

```http
202 Accepted
```

com o identificador externo do pedido.

Exemplo:

```json
{
  "external_id": "uuid",
  "status": "PENDING"
}
```

Os requisitos originais do desafio incluem CRUD, contagem, Find All, Find By ID e Find By Name. 

---

# 14. Swagger / OpenAPI

Somente a **Core API** terá documentação pública Swagger/OpenAPI.

A documentação deverá apresentar:

- endpoints;
- parâmetros;
- request bodies;
- responses;
- códigos HTTP;
- modelos de dados;
- exemplos de requisições;
- exemplos de respostas;
- header `Idempotency-Key` para criação de Orders.

Os serviços internos poderão possuir documentação técnica própria caso necessário, mas isso não é requisito do projeto.

---

# 15. Requisitos funcionais

## RF01 — Gerenciamento de Customers

O sistema deve permitir criar, consultar, atualizar e excluir Customers.

## RF02 — Consulta de Customers

O sistema deve permitir:

- listar todos os Customers;
- consultar Customer por ID;
- consultar Customer por nome;
- consultar quantidade de Customers.

## RF03 — Gerenciamento de Products

O sistema deve permitir criar, consultar, atualizar e excluir Products.

## RF04 — Consulta de Products

O sistema deve permitir:

- listar todos os Products;
- consultar Product por ID;
- consultar Product por nome;
- consultar quantidade de Products.

## RF05 — Criação de Orders

O sistema deve permitir que clientes/parceiros solicitem a criação de uma Order.

## RF06 — Processamento assíncrono

O sistema deve processar a criação da Order de forma assíncrona utilizando RabbitMQ.

## RF07 — Consulta de Orders

O sistema deve permitir consultar Orders persistidas.

## RF08 — Validação de Customer

O sistema deve validar a existência do Customer informado na Order.

## RF09 — Validação de Product

O sistema deve validar a existência dos Products informados na Order.

## RF10 — Validação de estoque

O sistema deve impedir a criação de uma Order quando a quantidade solicitada for superior ao estoque disponível.

## RF11 — Cálculo do pedido

O sistema deve calcular o valor total da Order a partir dos itens e respectivos preços.

## RF12 — Persistência do preço

O sistema deve registrar em cada OrderItem o preço utilizado no momento do processamento.

## RF13 — Cache

O sistema deve utilizar Redis para cachear dados de Customer e Product.

## RF14 — Idempotência

O sistema deve impedir que uma mesma requisição idempotente resulte em múltiplas Orders.

## RF15 — Retry

O sistema deve permitir novas tentativas para mensagens que falharem durante o processamento.

## RF16 — Dead Letter Queue

O sistema deve encaminhar mensagens que excederem o número máximo de tentativas para uma DLQ.

## RF17 — ACK

O Order Worker deve confirmar a mensagem no RabbitMQ somente após o processamento e persistência bem-sucedidos.

## RF18 — Escala horizontal

O sistema deve permitir a execução de múltiplas instâncias do Order Worker consumindo a mesma fila.

## RF19 — Documentação

A Core API deve disponibilizar documentação Swagger/OpenAPI.

## RF20 — Health Check

Os serviços devem disponibilizar mecanismos de verificação de saúde para facilitar o monitoramento do ambiente.

---

# 16. Requisitos não funcionais

## RNF01 — Disponibilidade

A arquitetura deve evitar dependência desnecessária entre o recebimento da requisição de criação de Order e o processamento completo do pedido.

## RNF02 — Escalabilidade

O processamento de Orders deve permitir escala horizontal por meio da execução de múltiplas instâncias do Order Worker.

## RNF03 — Resiliência

Falhas durante o processamento de mensagens não devem resultar automaticamente em perda da mensagem.

## RNF04 — Idempotência

O processamento deve ser seguro diante de redelivery ou repetição de mensagens.

## RNF05 — Consistência

O PostgreSQL deve ser a fonte de verdade para os dados persistidos. O Redis deve ser tratado como cache descartável.

## RNF06 — Performance

O sistema deve utilizar cache para reduzir chamadas repetitivas aos serviços de Customer e Product durante o processamento das Orders.

## RNF07 — Manutenibilidade

Os microsserviços devem seguir Hexagonal Architecture, mantendo domínio, casos de uso e infraestrutura desacoplados.

## RNF08 — Testabilidade

As regras de negócio devem poder ser testadas independentemente das tecnologias externas.

## RNF09 — Observabilidade

O sistema deve possuir logs estruturados e correlation IDs para facilitar o rastreamento das requisições e do processamento assíncrono.

## RNF10 — Documentação

A API pública deve ser documentada utilizando OpenAPI/Swagger.

## RNF11 — Portabilidade

O ambiente de desenvolvimento deve ser reproduzível utilizando Docker Compose.

## RNF12 — Segurança

As APIs devem validar entradas e evitar exposição desnecessária de informações internas.

## RNF13 — Separação de responsabilidades

Cada microsserviço deve ser responsável por seu próprio domínio e suas regras de negócio.

## RNF14 — Independência de persistência

Os componentes de domínio e aplicação não devem depender diretamente de PostgreSQL, Redis ou RabbitMQ.

## RNF15 — Integridade dos dados

O banco deve utilizar restrições de integridade, incluindo unicidade de `email` e `external_id`.

---

# 17. Infraestrutura Docker

O ambiente deverá ser composto por containers:

```text
docker-compose.yml

├── core-api
├── customer-service
├── product-service
├── order-service
├── order-worker
├── postgres
├── redis
└── rabbitmq
```

O Order Worker poderá ser escalado:

```bash
docker compose up --scale order-worker=3
```

O objetivo é demonstrar que múltiplas instâncias podem consumir a mesma fila.

---

# 18. Estrutura de projeto

Uma possível organização do monorepo:

```text
project/
├── core-api/
├── customer-service/
├── product-service/
├── order-service/
├── order-worker/
├── shared/
├── tests/
├── docker-compose.yml
├── .env.example
├── README.md
└── docs/
    ├── architecture/
    └── api/
```

Cada microsserviço deverá manter sua própria estrutura interna baseada em Hexagonal Architecture.

O compartilhamento entre serviços deve ser mínimo, evitando criar dependência entre domínios.

---

# 19. Fluxos principais

## Fluxo de Customer

```text
Client
  ↓
Core API
  ↓
Customer Service
  ↓
PostgreSQL
```

## Fluxo de Product

```text
Client
  ↓
Core API
  ↓
Product Service
  ↓
PostgreSQL
```

## Fluxo de criação de Order

```text
Client
  ↓
Core API
  ↓
Order Service
  ↓
RabbitMQ
  ↓
Order Worker
  ↓
Redis
  ├── Customer Service
  └── Product Service
  ↓
PostgreSQL
```

## Fluxo de falha

```text
Worker
  ↓
Processamento
  ↓
Falha
  ↓
Retry
  ↓
Falha novamente
  ↓
Limite de tentativas
  ↓
DLQ
```

---

# 20. Critérios de sucesso

O projeto será considerado funcional quando for possível:

1. Executar todo o ambiente através do Docker Compose.
2. Acessar a Core API.
3. Visualizar a documentação Swagger.
4. Criar, consultar, atualizar e excluir Customers.
5. Criar, consultar, atualizar e excluir Products.
6. Criar uma Order e receber `202 Accepted`.
7. Publicar o evento `OrderCreated` no RabbitMQ.
8. Processar a Order através do Worker.
9. Consultar Customer/Product utilizando Redis.
10. Utilizar fallback para os respectivos serviços em caso de cache miss.
11. Persistir a Order no PostgreSQL.
12. Impedir duplicidade através da idempotência e `UNIQUE external_id`.
13. Processar mensagens novamente após falhas.
14. Encaminhar mensagens excedentes para a DLQ.
15. Executar múltiplos Order Workers simultaneamente.
16. Consultar uma Order após seu processamento.

---

# 21. Escopo e decisões arquiteturais

Para manter o projeto simples e focado no objetivo do desafio:

- Customer e Product não utilizarão eventos de domínio.
- Apenas Order terá processamento assíncrono.
- Não será utilizado Cache Worker.
- Não haverá cache de Orders inicialmente.
- Redis será utilizado somente para Customer/Product e idempotência.
- RabbitMQ será utilizado somente para o fluxo de Orders.
- PostgreSQL será a fonte de verdade.
- Não será utilizado Kubernetes.
- Não será implementado Outbox Pattern inicialmente.
- O processamento de pagamentos não faz parte do escopo.
- Autenticação completa não faz parte do escopo inicial, podendo ser adicionada posteriormente.

---

# 22. Resultado arquitetural esperado

A solução final busca equilibrar simplicidade e demonstração dos conceitos do desafio.

```text
                           ┌───────────────┐
                           │     Client    │
                           └───────┬───────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │     Core API     │
                         │ Flask + Swagger  │
                         └───────┬──────────┘
                                 │
                 ┌───────────────┼────────────────┐
                 │               │                │
                 ▼               ▼                ▼
          Customer Service  Product Service  Order Service
                 │               │                │
                 ▼               ▼                ▼
             PostgreSQL      PostgreSQL       RabbitMQ
                                                  │
                                                  ▼
                                            Order Worker
                                           /      |      \
                                          /       |       \
                                      Redis   Customer   Product
                                                API        API
                                                  │
                                                  ▼
                                             Order DB
```

A arquitetura atende aos requisitos básicos do desafio e adiciona mecanismos de persistência, cache, processamento assíncrono, idempotência, retry, DLQ e escala horizontal.
