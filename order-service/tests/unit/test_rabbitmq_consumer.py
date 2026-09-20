"""Unit tests for the RabbitMQ consumer retry/ACK logic.

Pika channel and method objects are mocked so no broker connection is needed.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

from order_service.adapters.inbound.messaging.rabbitmq_consumer import RabbitMQConsumer

_MAX_RETRIES = 3


def _make_consumer(max_retries: int = _MAX_RETRIES) -> tuple[RabbitMQConsumer, MagicMock]:
    processor = MagicMock()
    processor_factory = MagicMock(return_value=processor)
    consumer = RabbitMQConsumer(
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        processor_factory=processor_factory,
        prefetch=1,
        max_retries=max_retries,
    )
    return consumer, processor


def _make_message(
    external_id: str | None = None,
    retry_count: int = 0,
    bad_json: bool = False,
) -> tuple[MagicMock, MagicMock, bytes]:
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = 1

    properties = MagicMock()
    properties.headers = {"x-retry-count": retry_count}
    properties.correlation_id = str(uuid.uuid4())

    if bad_json:
        body = b"not-json"
    else:
        payload = {
            "external_id": external_id or str(uuid.uuid4()),
            "customer_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
        }
        body = json.dumps(payload).encode()

    return channel, method, properties, body  # type: ignore[return-value]


class TestRabbitMQConsumerACK:
    def test_ack_after_successful_processing(self) -> None:
        consumer, processor = _make_consumer()
        channel, method, properties, body = _make_message()

        consumer._on_message(channel, method, properties, body)

        channel.basic_ack.assert_called_once_with(delivery_tag=method.delivery_tag)
        channel.basic_nack.assert_not_called()

    def test_nack_sent_when_retry_limit_exceeded(self) -> None:
        consumer, processor = _make_consumer(max_retries=3)
        processor.process.side_effect = RuntimeError("DB failure")
        channel, method, properties, body = _make_message(retry_count=3)

        consumer._on_message(channel, method, properties, body)

        channel.basic_nack.assert_called_once_with(delivery_tag=method.delivery_tag, requeue=False)
        channel.basic_ack.assert_not_called()

    def test_republish_with_incremented_retry_count_below_limit(self) -> None:
        consumer, processor = _make_consumer(max_retries=3)
        processor.process.side_effect = RuntimeError("transient error")
        channel, method, properties, body = _make_message(retry_count=0)

        consumer._on_message(channel, method, properties, body)

        # Original message is ACKed after republish.
        channel.basic_ack.assert_called_once_with(delivery_tag=method.delivery_tag)
        channel.basic_nack.assert_not_called()

        # A new message is published with retry count = 1.
        channel.basic_publish.assert_called_once()
        publish_kwargs = channel.basic_publish.call_args.kwargs
        assert publish_kwargs["properties"].headers["x-retry-count"] == 1

    def test_nack_on_malformed_message(self) -> None:
        consumer, _ = _make_consumer()
        channel, method, properties, body = _make_message(bad_json=True)

        consumer._on_message(channel, method, properties, body)

        channel.basic_nack.assert_called_once_with(delivery_tag=method.delivery_tag, requeue=False)
        channel.basic_ack.assert_not_called()
        channel.basic_publish.assert_not_called()

    def test_retry_at_limit_minus_one_republishes_not_dlq(self) -> None:
        """retry_count=2, max_retries=3 → still below limit → republish."""
        consumer, processor = _make_consumer(max_retries=3)
        processor.process.side_effect = RuntimeError("error")
        channel, method, properties, body = _make_message(retry_count=2)

        consumer._on_message(channel, method, properties, body)

        # Should republish, not NACK.
        channel.basic_publish.assert_called_once()
        channel.basic_nack.assert_not_called()
