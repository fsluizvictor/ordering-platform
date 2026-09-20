# Glossário

| Termo | Definição |
|---|---|
| Core API | Ponto único de entrada HTTP externo da plataforma. |
| Customer Service | Serviço responsável pelo domínio de clientes. |
| Product Service | Serviço responsável pelo domínio de produtos. |
| Order Service | Serviço HTTP responsável pelo recebimento e publicação de pedidos. |
| Order Worker | Processo consumidor responsável pelo processamento assíncrono dos pedidos. |
| Cache-Aside | Estratégia em que a aplicação consulta o cache e busca a fonte de verdade em caso de miss. |
| Idempotency-Key | Chave usada para evitar efeitos duplicados de uma mesma requisição. |
| external_id | Identificador externo único do pedido. |
| OrderCreated | Evento publicado quando um pedido é aceito para processamento. |
| DLQ | Dead Letter Queue, utilizada para mensagens que não puderam ser processadas após retries. |
| ACK | Confirmação de processamento de uma mensagem RabbitMQ. |
| Correlation ID | Identificador utilizado para rastrear uma operação entre serviços. |
| Bounded Context | Limite conceitual de um domínio e suas regras. |
| ACL | Anti-Corruption Layer, camada que protege o modelo interno contra contratos externos. |
