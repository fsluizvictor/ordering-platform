"""RabbitMQ consumer for the Order Worker.

Implements manual ACK with bounded retry via x-retry-count header.

Retry strategy
--------------
On processing failure the consumer republishes the message with an incremented
``x-retry-count`` header and ACKs the original.  This approach allows the
header value to be tracked across attempts without relying on requeue semantics,
which would leave the counter unchanged.

When the retry limit is exceeded the consumer NACKs with ``requeue=False`` so
RabbitMQ routes the message to the configured dead-letter exchange (orders.dlx)
and ultimately to the DLQ (orders.created.dlq).

ACK guarantee
-------------
ACK is issued only after the OrderProcessor commits to PostgreSQL.  If the
Worker dies before ACK, RabbitMQ redelivers the message.  The processor is
idempotent: orders already in COMPLETED or FAILED status are skipped.
"""

from __future__ import annotations

import json
import logging
import time

import pika
import pika.exceptions

from order_service.config.settings import (
    EXCHANGE_DLX,
    EXCHANGE_ORDERS,
    QUEUE_CREATED,
    QUEUE_DLQ,
    ROUTING_KEY_CREATED,
)

logger = logging.getLogger(__name__)

# Header key used to track retry attempts across redeliveries.
_RETRY_HEADER = "x-retry-count"

# Seconds to wait before reconnecting after a connection error.
_RECONNECT_DELAY = 5


class RabbitMQConsumer:
    """Blocking RabbitMQ consumer for OrderCreated messages."""

    def __init__(
        self,
        rabbitmq_url: str,
        processor_factory: ProcessorFactory,
        prefetch: int,
        max_retries: int,
    ) -> None:
        self._url = rabbitmq_url
        self._processor_factory = processor_factory
        self._prefetch = prefetch
        self._max_retries = max_retries

    def run(self) -> None:
        """Connect and consume indefinitely, reconnecting on connection errors."""
        while True:
            try:
                self._consume()
            except pika.exceptions.AMQPConnectionError as exc:
                logger.error(
                    "RabbitMQ connection lost, reconnecting",
                    extra={"error": str(exc), "delay": _RECONNECT_DELAY},
                )
                time.sleep(_RECONNECT_DELAY)
            except KeyboardInterrupt:
                logger.info("Worker shutting down")
                break

    # ── Internal ─────────────────────────────────────────────────────────────

    def _consume(self) -> None:
        params = pika.URLParameters(self._url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.basic_qos(prefetch_count=self._prefetch)
        _declare_topology(channel)

        logger.info("Waiting for messages on queue", extra={"queue": QUEUE_CREATED})

        channel.basic_consume(
            queue=QUEUE_CREATED,
            on_message_callback=self._on_message,
            auto_ack=False,
        )
        channel.start_consuming()

    def _on_message(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        headers: dict[str, object] = dict(properties.headers or {})
        retry_count = int(headers.get(_RETRY_HEADER, 0))
        correlation_id = properties.correlation_id or ""

        try:
            payload = json.loads(body.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            # Malformed message — no point in retrying; send straight to DLQ.
            logger.error(
                "Unparseable message, sending to DLQ",
                extra={"error": str(exc), "correlation_id": correlation_id},
            )
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        logger.info(
            "Received OrderCreated",
            extra={
                "external_id": payload.get("external_id"),
                "retry_count": retry_count,
                "correlation_id": correlation_id,
            },
        )

        try:
            processor = self._processor_factory()
            processor.process(payload)
            # ACK only after successful commit in the processor.
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(
                "Message ACKed",
                extra={
                    "external_id": payload.get("external_id"),
                    "correlation_id": correlation_id,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Order processing failed",
                extra={
                    "external_id": payload.get("external_id"),
                    "retry_count": retry_count,
                    "error": str(exc),
                    "correlation_id": correlation_id,
                },
                exc_info=True,
            )
            self._handle_failure(channel, method, properties, body, retry_count)

    def _handle_failure(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
        retry_count: int,
    ) -> None:
        if retry_count < self._max_retries:
            # Republish with incremented counter and ACK the original so the
            # counter is reliably tracked across redeliveries.
            new_count = retry_count + 1
            new_headers = dict(properties.headers or {})
            new_headers[_RETRY_HEADER] = new_count
            channel.basic_publish(
                exchange=EXCHANGE_ORDERS,
                routing_key=ROUTING_KEY_CREATED,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                    correlation_id=properties.correlation_id,
                    headers=new_headers,
                ),
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.warning(
                "Message requeued for retry",
                extra={"retry_count": new_count, "max_retries": self._max_retries},
            )
        else:
            # Retry budget exhausted — NACK so DLX routes to DLQ.
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            logger.error(
                "Retry limit exceeded, message sent to DLQ",
                extra={"retry_count": retry_count, "max_retries": self._max_retries},
            )


# ── Type alias for readability ────────────────────────────────────────────────

# A factory callable that returns an OrderProcessor bound to a fresh DB session.
ProcessorFactory = "type[OrderProcessor]"  # used only for type comments


# ── Topology ─────────────────────────────────────────────────────────────────


def _declare_topology(channel: pika.adapters.blocking_connection.BlockingChannel) -> None:
    """Idempotently declare exchanges and queues.

    Matches the topology declared by the Order Service publisher so both
    processes can start in any order without topology conflicts.
    """
    channel.exchange_declare(exchange=EXCHANGE_DLX, exchange_type="direct", durable=True)
    channel.queue_declare(queue=QUEUE_DLQ, durable=True)
    channel.queue_bind(queue=QUEUE_DLQ, exchange=EXCHANGE_DLX, routing_key=QUEUE_CREATED)

    channel.exchange_declare(exchange=EXCHANGE_ORDERS, exchange_type="direct", durable=True)
    channel.queue_declare(
        queue=QUEUE_CREATED,
        durable=True,
        arguments={
            "x-dead-letter-exchange": EXCHANGE_DLX,
            "x-dead-letter-routing-key": QUEUE_CREATED,
        },
    )
    channel.queue_bind(
        queue=QUEUE_CREATED, exchange=EXCHANGE_ORDERS, routing_key=ROUTING_KEY_CREATED
    )
