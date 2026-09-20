# Guia de Desenvolvimento

## Pré-requisitos

- Python 3.12
- Docker
- Docker Compose
- Git

Convenções táticas (filas, erros, health, Order PENDING): `docs/conventions.md`.

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

Na raiz:

```bash
make lint
make format
make typecheck
make test
```

Ferramentas de lint/format estão no `pyproject.toml`.

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

Seguir `docs/conventions.md`:

1. Skeleton / Docker / tooling
2. Customer Service
3. Product Service
4. Core API (proxy + OpenAPI)
5. Order Service HTTP + publicação
6. Order Worker + Redis Cache-Aside
7. Idempotência
8. Retry / DLQ
9. Testes de integração
10. Observabilidade e documentação
