# Guia de Execução por Fase

Tabela de modelos recomendados e prompts otimizados para cada fase da implementação.

---

## Tabela de modelos por fase

| Fase | Complexidade | Modelo recomendado | Justificativa |
|---|---|---|---|
| **0** — Preparation | ✅ Concluída | — | Já implementada |
| **1** — Docker Infra | 🟢 Baixa | `gemini-3.5-flash` | YAML declarativo, zero lógica de negócio |
| **2** — Customer Service | 🟡 Média | `claude-4.6-sonnet-medium-thinking` | Primeiro serviço — padrão hexagonal precisa sair certo; será referência para Phase 3 |
| **3** — Product Service | 🟢 Baixa | `gemini-3.5-flash` | Cópia do padrão do Phase 2; modelo pode referenciar o código existente |
| **4** — Core API | 🟡 Média | `claude-4.6-sonnet-medium-thinking` | Proxy + Swagger + correlation ID — precisa de consistência com convenções |
| **5** — Order Service | 🟡 Média | `claude-4.6-sonnet-medium-thinking` | Domínio de Order + evento + HTTP + publish — bem documentado, sem surpresas |
| **6** — Order Worker | 🔴 Alta | `claude-sonnet-5-thinking-high` | Fase mais complexa: async, Cache-Aside, Retry/DLQ, ACK manual |
| **7** — Observability | 🟢 Baixa | `claude-4.5-haiku-thinking` | `shared/` já tem tudo pronto; é só garantir que está conectado |
| **8** — E2E Tests | 🟡 Média | `claude-4.6-sonnet-medium-thinking` | Testes com infra real; precisa de precisão nos asserts e polling |
| **9** — Hardening | 🟡 Média | `claude-4.6-sonnet-medium-thinking` | Review de type hints, erros, Docker — atenção a detalhes |

---

## Prompts por fase

---

### Phase 1 — Docker Infrastructure

**Modelo:** `gemini-3.5-flash`

```
Leia os seguintes arquivos antes de começar:
- docs/conventions.md
- docs/phases/phase-1-docker.md
- .env.example

Contexto:
- O repositório já possui estrutura de diretórios, pyproject.toml, shared/ e os esquelets dos serviços.
- Nenhum docker-compose.yml existe ainda.
- Phase 0 está concluída.

Tarefa:
Implemente a PHASE 1 — Docker Infrastructure conforme docs/phases/phase-1-docker.md.

Crie apenas:
1. docker-compose.yml com os serviços: postgres, redis, rabbitmq (infraestrutura apenas).
2. Configurações de volumes, rede, health checks e variáveis de ambiente.

Não crie Dockerfiles de serviços de aplicação — esses são criados em suas respectivas fases.

Após implementar:
1. Reporte os arquivos criados/modificados.
2. Reporte se `docker compose up postgres redis rabbitmq` inicia os três serviços saudáveis.
3. Marque os critérios de aceite como satisfeitos ou liste pendências.
4. Não avance para a Phase 2.
```

---

### Phase 2 — Customer Service

**Modelo:** `claude-4.6-sonnet-medium-thinking`

```
Leia os seguintes arquivos antes de começar:
- docs/conventions.md
- docs/decisions.md
- docs/phases/phase-2-customer-service.md
- shared/http.py
- shared/errors.py
- shared/correlation.py
- shared/env.py
- customer-service/src/customer_service/config/settings.py
- customer-service/src/customer_service/adapters/inbound/http/app.py
- customer-service/src/customer_service/main.py

Contexto:
- A infraestrutura Docker (Phase 1) está concluída.
- O esqueleto do customer-service já existe com __init__.py em todos os diretórios.
- O shared/ possui logging, correlation, error helpers e create_service_app() prontos.
- Python 3.12, Flask, SQLAlchemy, Pytest.

Tarefa:
Implemente a PHASE 2 — Customer Service conforme docs/phases/phase-2-customer-service.md.

Atenção especial:
- Este serviço será o padrão de referência para o Product Service. Implemente com cuidado.
- Siga Hexagonal Architecture: entidades e regras de domínio não dependem de Flask ou SQLAlchemy.
- Use os helpers de shared/ já existentes (não reimplemente logging, health, errors).
- Escreva os testes unitários junto com o código.

Após implementar:
1. Execute os testes: reporte resultado completo.
2. Execute `ruff check . && ruff format .`: reporte resultado.
3. Reporte todos os arquivos criados/modificados.
4. Valide cada critério de aceite da fase.
5. Não avance para a Phase 3.
```

---

### Phase 3 — Product Service

**Modelo:** `gemini-3.5-flash`

```
Leia os seguintes arquivos antes de começar:
- docs/conventions.md
- docs/phases/phase-3-product-service.md
- customer-service/src/customer_service/domain/entities/customer.py
- customer-service/src/customer_service/adapters/inbound/http/app.py
- customer-service/src/customer_service/adapters/outbound/persistence/
- customer-service/tests/unit/

Contexto:
- O Customer Service (Phase 2) está concluído e funcional.
- O Product Service deve seguir exatamente o mesmo padrão hexagonal do Customer Service.
- Use o Customer Service como referência estrutural direta.

Tarefa:
Implemente a PHASE 3 — Product Service conforme docs/phases/phase-3-product-service.md.
Espelhe a estrutura do Customer Service adaptando para o domínio de Product.

Diferenças em relação ao Customer Service:
- Entidade: name, description, price (Decimal, > 0), stock (int, >= 0)
- Sem constraint UNIQUE além do id
- Porta: 8002, env var: PRODUCT_DATABASE_URL

Após implementar:
1. Execute os testes: reporte resultado completo.
2. Execute `ruff check . && ruff format .`: reporte resultado.
3. Reporte todos os arquivos criados/modificados.
4. Valide cada critério de aceite da fase.
5. Não avance para a Phase 4.
```

---

### Phase 4 — Core API

**Modelo:** `claude-4.6-sonnet-medium-thinking`

```
Leia os seguintes arquivos antes de começar:
- docs/conventions.md
- docs/phases/phase-4-core-api.md
- shared/http.py
- shared/correlation.py
- shared/errors.py
- core-api/src/core_api/

Contexto:
- Customer Service (:8001) e Product Service (:8002) estão concluídos e rodando.
- O esqueleto do core-api existe mas está vazio (sem main.py, sem config).
- A Core API não tem banco de dados e não contém regras de negócio.
- Rotas públicas usam prefixo /api/v1; serviços internos usam raiz.
- Swagger/OpenAPI deve ser exposto em GET /docs e GET /openapi.yaml.

Tarefa:
Implemente a PHASE 4 — Core API conforme docs/phases/phase-4-core-api.md.

Atenção especial:
- Propague X-Correlation-ID em todas as chamadas proxy para serviços internos.
- A rota /api/v1/orders será conectada ao Order Service na Phase 5 — deixe o placeholder.
- Documente Customer e Product no Swagger (Orders será adicionado na Phase 5).

Após implementar:
1. Execute os testes: reporte resultado completo.
2. Execute `ruff check . && ruff format .`: reporte resultado.
3. Confirme que GET /api/v1/customers e GET /api/v1/products funcionam via Core API.
4. Confirme que Swagger UI abre em http://localhost:8000/docs.
5. Reporte todos os arquivos criados/modificados.
6. Não avance para a Phase 5.
```

---

### Phase 5 — Order Service

**Modelo:** `claude-4.6-sonnet-medium-thinking`

```
Leia os seguintes arquivos antes de começar:
- docs/conventions.md
- docs/decisions.md
- docs/phases/phase-5-order-service.md
- order-service/src/order_service/config/settings.py
- order-service/src/order_service/adapters/inbound/http/app.py
- shared/http.py

Contexto:
- Core API, Customer Service e Product Service estão concluídos.
- O esqueleto do order-service já existe com config/settings.py preenchido
  (contém constantes de RabbitMQ: EXCHANGE_ORDERS, QUEUE_CREATED, QUEUE_DLQ etc.).
- Order Service e Order Worker compartilham o mesmo pacote Python (order_service).
- O Worker será implementado na Phase 6 — não implementar consumo nesta fase.

Tarefa:
Implemente a PHASE 5 — Order Service conforme docs/phases/phase-5-order-service.md.

Atenção especial:
- POST /orders deve: validar → gerar external_id → persistir PENDING → publicar → retornar 202.
- Persistir ANTES de publicar no RabbitMQ (ver ADR-011 em docs/decisions.md).
- O Worker não cria o pedido do zero — ele processa o PENDING existente.
- Inclua a estrutura adapters/inbound/messaging/ (vazia) para o Worker da Phase 6.
- Adicione /api/v1/orders ao Swagger da Core API.

Após implementar:
1. Execute testes unitários e integração: reporte resultado completo.
2. Execute `ruff check . && ruff format .`: reporte resultado.
3. Confirme: POST retorna 202, mensagem aparece no RabbitMQ, GET /orders/{id} retorna PENDING.
4. Reporte todos os arquivos criados/modificados.
5. Não avance para a Phase 6.
```

---

### Phase 6 — Order Worker

**Modelo:** `claude-sonnet-5-thinking-high`

```
Leia os seguintes arquivos antes de começar:
- docs/conventions.md
- docs/decisions.md
- docs/phases/phase-6-order-worker.md
- order-service/src/order_service/domain/
- order-service/src/order_service/application/
- order-service/src/order_service/adapters/outbound/persistence/
- order-service/src/order_service/config/settings.py

Contexto:
- Order Service (Phase 5) está concluído: persiste PENDING e publica OrderCreated.
- O Worker deve processar o registro PENDING existente — não criar Order do zero.
- Order Service e Worker compartilham o mesmo pacote Python (order_service).
- O Worker roda como: python -m order_service.worker
- order-worker/ contém apenas Dockerfile apontando para o mesmo build context do order-service.

Tarefa:
Implemente a PHASE 6 — Order Worker conforme docs/phases/phase-6-order-worker.md.

Componentes a implementar:
1. RabbitMQ consumer com manual ACK (adapters/inbound/messaging/).
2. Redis Cache-Aside para Customer e Product (adapters/outbound/cache/).
3. HTTP clients para Customer/Product Service em cache miss (adapters/outbound/external_services/).
4. Lógica de processamento: validação, cálculo de total, unit_price, persistência.
5. Retry limitado via x-retry-count + NACK; DLQ via x-dead-letter-exchange.
6. worker.py como entrypoint.
7. Dockerfile para order-worker/ (CMD: python -m order_service.worker).

Restrições críticas:
- ACK somente após COMMIT bem-sucedido no PostgreSQL.
- Nunca ACK antes de persistir.
- Nunca criar loop infinito de requeue.
- MAX_RETRIES lido de ORDER_MAX_RETRIES (env var).
- Cache não é fonte de verdade — fallback para serviços HTTP sempre em MISS.

Após implementar:
1. Execute testes unitários e integração: reporte resultado completo.
2. Execute `ruff check . && ruff format .`: reporte resultado.
3. Confirme fluxo completo: POST /orders → 202 → Worker → COMPLETED no banco.
4. Confirme que docker compose up --scale order-worker=3 sobe 3 Workers.
5. Confirme que mensagem com erro vai para DLQ após MAX_RETRIES.
6. Reporte todos os arquivos criados/modificados.
7. Não avance para a Phase 7.
```

---

### Phase 7 — Observability

**Modelo:** `claude-4.5-haiku-thinking`

```
Leia os seguintes arquivos antes de começar:
- docs/phases/phase-7-observability.md
- shared/logging_setup.py
- shared/correlation.py

Contexto:
- O shared/ já possui JsonFormatter, ServiceFilter e setup_logging prontos.
- O shared/ já possui init_correlation para Flask (gera X-Request-ID e X-Correlation-ID).
- Esta fase não introduz nova infraestrutura — apenas garante que tudo está conectado.

Tarefa:
Implemente a PHASE 7 — Observability conforme docs/phases/phase-7-observability.md.

Verifique e corrija (sem reescrever o que já funciona):
1. setup_logging() chamado em todos os entrypoints (main.py, worker.py).
2. init_correlation() chamado em todos os Flask apps.
3. X-Correlation-ID propagado nas chamadas proxy da Core API.
4. correlation_id lido do evento OrderCreated no Worker e incluído nos logs.
5. Logs de criação, publicação, consumo, falhas e DLQ presentes.

Após implementar:
1. Reporte exatamente quais arquivos foram modificados e o que mudou em cada um.
2. Valide cada critério de aceite da fase.
3. Não avance para a Phase 8.
```

---

### Phase 8 — End-to-End Tests

**Modelo:** `claude-4.6-sonnet-medium-thinking`

```
Leia os seguintes arquivos antes de começar:
- docs/conventions.md
- docs/phases/phase-8-e2e-tests.md

Contexto:
- Todas as fases anteriores (0–7) estão concluídas.
- Os testes E2E rodam contra o ambiente Docker Compose real (não mocks).
- Base URL pública: http://localhost:8000/api/v1

Tarefa:
Implemente a PHASE 8 — End-to-End Tests conforme docs/phases/phase-8-e2e-tests.md.

Os 4 cenários obrigatórios:
1. Happy Path: Customer + Product → Order → COMPLETED + total correto.
2. Customer inexistente → Order → FAILED.
3. Product inexistente → Order → FAILED.
4. Estoque insuficiente → Order → FAILED.

Para cenários assíncronos, use polling com timeout (máx 10s) para aguardar o Worker.

Após implementar:
1. Execute os testes com docker compose up: reporte resultado completo.
2. Reporte todos os arquivos criados/modificados.
3. Valide cada critério de aceite da fase.
4. Não avance para a Phase 9.
```

---

### Phase 9 — Hardening

**Modelo:** `claude-4.6-sonnet-medium-thinking`

```
Leia os seguintes arquivos antes de começar:
- docs/phases/phase-9-hardening.md
- PLAN.md (seção Fora do escopo)

Contexto:
- Todas as fases anteriores estão concluídas e testadas.
- Esta é a fase final de polimento — não adicionar funcionalidades novas.

Tarefa:
Implemente a PHASE 9 — Hardening conforme docs/phases/phase-9-hardening.md.

Execute nesta ordem:
1. `ruff check .` → corrija todas as violações.
2. `ruff format .` → aplique formatação.
3. `mypy` → corrija todos os erros de tipo.
4. Revise exception handling: sem bare except, sem swallow silencioso.
5. Confirme constraints UNIQUE(email) e UNIQUE(external_id) nas migrations.
6. Confirme health checks e restart policies no docker-compose.yml.
7. Valide que .env.example cobre todas as env vars lidas pelo código.

Ao final:
1. Execute: docker compose down -v && docker compose up --build
2. Execute: make test && make lint && make typecheck
3. Reporte resultado de cada gate de qualidade.
4. Reporte os arquivos modificados.
5. Declare a fase concluída ou liste pendências.
```
