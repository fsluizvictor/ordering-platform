# Guia de Desenvolvimento

## Pré-requisitos

- Python 3.x
- Docker
- Docker Compose
- Git

## Inicialização

A partir da raiz:

```bash
docker compose up --build
```

Para executar em background:

```bash
docker compose up -d --build
```

## Escalar workers

```bash
docker compose up --scale order-worker=3
```

## Logs

```bash
docker compose logs -f
```

Somente Order Worker:

```bash
docker compose logs -f order-worker
```

## Testes

Os testes devem ser executáveis de forma automatizada.

Exemplo:

```bash
pytest
```

## Qualidade

Antes de abrir um PR/commit relevante:

```bash
pytest
```

Ferramentas de lint/format devem ser centralizadas no `pyproject.toml`.

## Variáveis de ambiente

Cada serviço deve possuir configuração por ambiente.

Exemplos:

```text
DATABASE_URL=
REDIS_URL=
RABBITMQ_URL=
LOG_LEVEL=
SERVICE_NAME=
```

Não versionar segredos reais.

Utilizar `.env.example` como referência.

## Swagger

Somente o Core API deve expor a documentação pública consolidada da API.

O contrato deve permanecer sincronizado com as implementações.

## Fluxo recomendado de implementação

1. Criar infraestrutura Docker.
2. Criar Customer Service.
3. Criar Product Service.
4. Criar Redis e Cache-Aside.
5. Criar Order Service.
6. Criar RabbitMQ.
7. Criar Order Worker.
8. Implementar idempotência.
9. Implementar retry/DLQ.
10. Criar Core API.
11. Integrar Swagger.
12. Criar testes de integração.
13. Validar fluxo completo.
