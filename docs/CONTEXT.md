# Contexto do Projeto

## Objetivo

Construir uma plataforma de vendas online para uma grande empresa de comércio eletrônico, disponibilizando dados de clientes, produtos e pedidos para parceiros externos por meio de uma API REST.

O sistema deve permitir operações CRUD para clientes, produtos e pedidos, além de consultas por ID, nome e contagem de registros.

## Escopo arquitetural

A solução é composta por:

- Core API
- Customer Service
- Product Service
- Order Service
- Order Worker
- PostgreSQL
- Redis
- RabbitMQ

O Core API é o ponto de entrada HTTP externo. Customer, Product e Order são contextos independentes. A criação de pedidos é assíncrona.

## Princípios

- Cada serviço deve possuir responsabilidade bem definida.
- Regras de negócio devem permanecer nos respectivos domínios.
- Não compartilhar entidades de domínio entre serviços.
- PostgreSQL é a fonte de verdade dos dados persistidos.
- Redis é utilizado como cache de Customer e Product.
- RabbitMQ é utilizado no fluxo assíncrono de criação de pedidos.
- O processamento de mensagens deve ser idempotente.
- Alterações arquiteturais devem ser documentadas antes de serem implementadas.
