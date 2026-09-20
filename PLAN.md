# PLAN.md — Online Sales Platform

## Leitura obrigatória antes de qualquer fase

```text
1. docs/conventions.md          ← contratos, nomes, fluxos táticos (SEMPRE ler)
2. docs/decisions.md            ← ADRs
3. docs/phases/phase-N-*.md     ← somente a fase a ser implementada
```

Não carregar este arquivo inteiro em toda sessão. Ler apenas o arquivo da fase corrente.

---

## Regras de execução

1. **Uma fase por vez.** Não implementar fases futuras.
2. **Cada fase deve:** ser implementada → testes escritos → testes executados → critérios verificados.
3. **Não avançar automaticamente.** Aguardar instrução explícita para a próxima fase.
4. **Antes de modificar código:** inspecionar o estado atual do projeto e identificar conflitos.
5. **Após implementar:** rodar `ruff check .`, `ruff format .`, testes relevantes e reportar resultado.

---

## Arquitetura

Hexagonal Architecture em todos os serviços.

```text
Adapters → Application → Domain
```

O domínio não depende de Flask, SQLAlchemy, PostgreSQL, Redis, RabbitMQ, Pika ou Docker.
Dependências de infraestrutura são acessadas através de ports/interfaces.

---

## Estratégia de testes

| Serviço | Unitários | Integração |
|---|---|---|
| Customer Service | Sim — todas as regras de domínio | Não |
| Product Service | Sim — todas as regras de domínio | Não |
| Core API | Sim — roteamento, validação, erros | Não |
| Order Service | Sim — regras de domínio e HTTP | Sim — 1 happy path |
| Order Worker | Sim — lógica de processamento | Sim — 1 happy path |

---

## Ordem de implementação

```text
PHASE 0 → docs/phases/phase-0-preparation.md
PHASE 1 → docs/phases/phase-1-docker.md
PHASE 2 → docs/phases/phase-2-customer-service.md
PHASE 3 → docs/phases/phase-3-product-service.md
PHASE 4 → docs/phases/phase-4-core-api.md
PHASE 5 → docs/phases/phase-5-order-service.md
PHASE 6 → docs/phases/phase-6-order-worker.md
PHASE 7 → docs/phases/phase-7-observability.md
PHASE 8 → docs/phases/phase-8-e2e-tests.md
PHASE 9 → docs/phases/phase-9-hardening.md
```

Não alterar esta ordem sem justificativa arquitetural explícita.

---

## Definition of Done

Uma fase só está completa quando:

```text
[ ] Código implementado
[ ] Testes implementados e passando
[ ] Critérios de aceite da fase satisfeitos
[ ] Docker funcionando (quando aplicável)
[ ] Sem regressões nas fases anteriores
[ ] Arquitetura preservada (domínio sem dependência de infra)
```

Reportar explicitamente quando a fase estiver completa e listar pendências antes de prosseguir.

---

## Fora do escopo (não implementar sem solicitação explícita)

- Kubernetes
- Autenticação / autorização
- Pagamentos
- Decremento de estoque
- `Idempotency-Key` header + Redis NX (ver `docs/decisions.md` ADR-007)
- Cache de Orders
- Outbox Pattern
- Eventos de domínio para Customer ou Product
- Service mesh / cloud infrastructure

---

## Status do projeto

```text
[ ] PHASE 0 — Preparation
[ ] PHASE 1 — Docker Infrastructure
[ ] PHASE 2 — Customer Service
[ ] PHASE 3 — Product Service
[ ] PHASE 4 — Core API
[ ] PHASE 5 — Order Service
[ ] PHASE 6 — Order Worker
[ ] PHASE 7 — Observability
[ ] PHASE 8 — End-to-End Tests
[ ] PHASE 9 — Hardening and Final Documentation
```
