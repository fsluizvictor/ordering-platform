# Checklist de Implementação

## Infraestrutura

- [ ] Docker Compose
- [ ] PostgreSQL
- [ ] Redis
- [ ] RabbitMQ
- [ ] Variáveis de ambiente
- [ ] Health checks

## Customer

- [ ] Entidade
- [ ] Repository
- [ ] Service
- [ ] CRUD
- [ ] Busca por nome
- [ ] Count
- [ ] Validações
- [ ] Testes
- [ ] Persistência
- [ ] Invalidação de cache

## Product

- [ ] Entidade
- [ ] Repository
- [ ] Service
- [ ] CRUD
- [ ] Busca por nome
- [ ] Count
- [ ] Validações
- [ ] Testes
- [ ] Persistência
- [ ] Invalidação de cache

## Order

- [ ] Entidades Order e OrderItem
- [ ] Repository
- [ ] Service
- [ ] Geração de external_id
- [ ] Idempotency-Key
- [ ] Publicação OrderCreated
- [ ] POST retornando 202
- [ ] Consultas
- [ ] Count
- [ ] Atualização
- [ ] Remoção
- [ ] Testes

## Worker

- [ ] Consumer RabbitMQ
- [ ] Manual ACK
- [ ] Prefetch
- [ ] Consulta Redis
- [ ] Fallback Customer API
- [ ] Fallback Product API
- [ ] Validação das regras
- [ ] Cálculo do total
- [ ] Persistência
- [ ] Idempotência
- [ ] Retry
- [ ] DLQ
- [ ] Testes

## Core API

- [ ] Routing
- [ ] Proxy/HTTP clients
- [ ] Correlation ID
- [ ] Tratamento de erros
- [ ] Swagger/OpenAPI
- [ ] Health check
- [ ] Testes

## Finalização

- [ ] Fluxo completo Customer
- [ ] Fluxo completo Product
- [ ] Fluxo completo Order
- [ ] Testes de integração
- [ ] Logs
- [ ] README atualizado
- [ ] Diagrama atualizado
