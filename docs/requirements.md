# Requisitos

## Requisitos funcionais

### Clientes

- RF01 — Criar cliente.
- RF02 — Listar clientes.
- RF03 — Buscar cliente por ID.
- RF04 — Buscar clientes por nome.
- RF05 — Atualizar cliente.
- RF06 — Remover cliente.
- RF07 — Consultar quantidade de clientes.

### Produtos

- RF08 — Criar produto.
- RF09 — Listar produtos.
- RF10 — Buscar produto por ID.
- RF11 — Buscar produtos por nome.
- RF12 — Atualizar produto.
- RF13 — Remover produto.
- RF14 — Consultar quantidade de produtos.

### Pedidos

- RF15 — Criar pedido.
- RF16 — Consultar pedido por external_id.
- RF17 — Listar pedidos.
- RF18 — Atualizar pedido.
- RF19 — Remover pedido.
- RF20 — Consultar quantidade de pedidos.

## Regras de negócio

### Customer

- Nome é obrigatório e não pode ser vazio.
- E-mail é obrigatório.
- E-mail deve ser único.

### Product

- Nome é obrigatório.
- Preço deve ser maior que zero.
- Estoque não pode ser negativo.

### Order

- Um pedido deve possuir pelo menos um item.
- A quantidade de cada item deve ser maior que zero.
- O cliente deve existir.
- Os produtos devem existir.
- A quantidade solicitada não pode exceder o estoque disponível.
- O total do pedido deve ser calculado pelo sistema.
- O preço utilizado no item deve ser armazenado no momento da criação do pedido.
- external_id deve ser único.
- A criação do pedido deve ser idempotente.
- Status possíveis: PENDING, PROCESSING, COMPLETED e FAILED.

## Requisitos não funcionais

- RNF01 — APIs devem seguir REST.
- RNF02 — Serviços devem ser independentes.
- RNF03 — Dados persistidos devem utilizar PostgreSQL.
- RNF04 — Cache deve utilizar Redis.
- RNF05 — Comunicação assíncrona deve utilizar RabbitMQ.
- RNF06 — Processamento de mensagens deve utilizar ACK manual.
- RNF07 — Falhas de processamento devem possuir retry limitado e DLQ.
- RNF08 — APIs devem possuir logs estruturados.
- RNF09 — Requisições devem possuir correlation/request ID.
- RNF10 — A documentação pública da API deve utilizar OpenAPI/Swagger.
- RNF11 — Serviços devem ser executáveis via Docker Compose.
- RNF12 — Configurações devem ser fornecidas por variáveis de ambiente.
- RNF13 — Testes automatizados devem cobrir regras de negócio e integrações relevantes.
- RNF14 — Não registrar dados sensíveis desnecessariamente nos logs.
- RNF15 — O sistema deve permitir múltiplas instâncias do Order Worker.

## Critérios de aceitação

A implementação será considerada aderente quando:

1. Os CRUDs de Customer e Product funcionarem.
2. O fluxo de criação de Order retornar `202 Accepted`.
3. O Order Worker processar o evento de criação.
4. O pedido processado for persistido no PostgreSQL.
5. Customer e Product forem consultados primeiro pelo Redis durante o processamento.
6. Cache miss resultar em consulta síncrona ao serviço correspondente.
7. Mensagens processadas com sucesso forem ACKadas.
8. Falhas forem submetidas ao mecanismo de retry e posteriormente DLQ quando excederem o limite.
9. Requisições duplicadas não criarem pedidos duplicados.
