"""RabbitMQ implementation of the OrderPublisher port.

Publishes OrderCreated events as JSON to the configured exchange.
The exchange and queue are declared on first use (idempotent declarations)
so the publisher works whether the Worker has started yet or not.
"""

from __future__ import annotations

import json
import logging

import pika
import pika.exceptions

from order_service.config.settings import (
    EXCHANGE_DLX,
    EXCHANGE_ORDERS,
    QUEUE_CREATED,
    QUEUE_DLQ,
    ROUTING_KEY_CREATED,
)
from order_service.domain.ports.order_publisher import OrderCreatedEvent, OrderPublisher

logger = logging.getLogger(__name__)


class RabbitMQOrderPublisher(OrderPublisher):
    """Publishes order events to RabbitMQ.

    Opens a fresh connection per publish call to keep the adapter
    stateless and safe for multi-threaded Flask workers.
    """

    def __init__(self, rabbitmq_url: str) -> None:
        self._url = rabbitmq_url

    def publish_order_created(self, event: OrderCreatedEvent) -> None:
        payload = {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "occurred_at": event.occurred_at.isoformat(),
            "correlation_id": str(event.correlation_id) if event.correlation_id else None,
            "external_id": str(event.external_id),
            "customer_id": str(event.customer_id),
            "items": [
                {
                    "product_id": str(item.product_id),
                    "quantity": item.quantity,
                }
                for item in event.items
            ],
        }
        body = json.dumps(payload).encode()

        log_extra = {
            "event_id": str(event.event_id),
            "external_id": str(event.external_id),
        }
        if event.correlation_id:
            log_extra["correlation_id"] = str(event.correlation_id)

        params = pika.URLParameters(self._url)
        connection = pika.BlockingConnection(params)
        try:
            channel = connection.channel()
            _declare_topology(channel)
            channel.basic_publish(
                exchange=EXCHANGE_ORDERS,
                routing_key=ROUTING_KEY_CREATED,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                    correlation_id=str(event.correlation_id) if event.correlation_id else None,
                    message_id=str(event.event_id),
                ),
            )
            logger.debug("Published OrderCreated", extra=log_extra)
        finally:
            try:
                connection.close()
            except Exception:
                pass


def _declare_topology(channel: pika.adapters.blocking_connection.BlockingChannel) -> None:
    """Idempotently declare exchanges and queues.

    Declaring with the same parameters is safe even if the topology
    was already created by the Order Worker.
    """
    # Dead-letter exchange
    channel.exchange_declare(
        exchange=EXCHANGE_DLX,
        exchange_type="direct",
        durable=True,
    )
    # DLQ — receives messages that exhaust their retry budget
    channel.queue_declare(
        queue=QUEUE_DLQ,
        durable=True,
    )
    channel.queue_bind(queue=QUEUE_DLQ, exchange=EXCHANGE_DLX, routing_key=QUEUE_CREATED)

    # Main orders exchange
    channel.exchange_declare(
        exchange=EXCHANGE_ORDERS,
        exchange_type="direct",
        durable=True,
    )
    # Main work queue with DLX configured
    channel.queue_declare(
        queue=QUEUE_CREATED,
        durable=True,
        arguments={
            "x-dead-letter-exchange": EXCHANGE_DLX,
            "x-dead-letter-routing-key": QUEUE_CREATED,
        },
    )
    channel.queue_bind(
        queue=QUEUE_CREATED,
        exchange=EXCHANGE_ORDERS,
        routing_key=ROUTING_KEY_CREATED,
    )
