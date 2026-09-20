"""Integration tests — happy path.

These tests require a running PostgreSQL and RabbitMQ. They are skipped
automatically when the required environment variables are not set.

Run with:
    ORDER_DATABASE_URL=postgresql://... RABBITMQ_URL=amqp://... \
    pytest order-service/tests/integration/
"""

from __future__ import annotations

import json
import os
import uuid

import pika
import pytest

_DB_URL = os.environ.get("ORDER_DATABASE_URL", "")
_RMQURL = os.environ.get("RABBITMQ_URL", "")
_SKIP = not (_DB_URL and _RMQURL)

pytestmark = pytest.mark.skipif(
    _SKIP,
    reason="ORDER_DATABASE_URL and RABBITMQ_URL must be set for integration tests",
)


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("ORDER_DATABASE_URL", _DB_URL)
    os.environ.setdefault("RABBITMQ_URL", _RMQURL)
    from order_service.adapters.inbound.http.app import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def _consume_one_message(queue: str, timeout: int = 5) -> dict | None:
    """Consume one message from a RabbitMQ queue and immediately NACK it
    (so the message is re-queued) to avoid interfering with the Worker."""
    params = pika.URLParameters(_RMQURL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    method_frame, header_frame, body = channel.basic_get(queue=queue, auto_ack=False)
    if method_frame:
        # NACK without requeue so the test doesn't consume production messages.
        # In CI this is safe because the queue is isolated.
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        connection.close()
        return json.loads(body)
    connection.close()
    return None


class TestOrderIntegrationHappyPath:
    def test_post_order_returns_202(self, client) -> None:
        payload = {
            "customer_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 3}],
        }
        resp = client.post("/orders", json=payload)
        assert resp.status_code == 202
        data = resp.get_json()
        assert "external_id" in data
        assert data["status"] == "PENDING"

    def test_get_order_returns_pending_immediately_after_creation(self, client) -> None:
        customer_id = str(uuid.uuid4())
        product_id = str(uuid.uuid4())
        payload = {
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": 1}],
        }
        create_resp = client.post("/orders", json=payload)
        assert create_resp.status_code == 202

        external_id = create_resp.get_json()["external_id"]
        get_resp = client.get(f"/orders/{external_id}")
        assert get_resp.status_code == 200
        data = get_resp.get_json()
        assert data["status"] == "PENDING"
        assert data["external_id"] == external_id

    def test_order_created_message_published_to_rabbitmq(self, client) -> None:
        from order_service.config.settings import QUEUE_CREATED

        customer_id = str(uuid.uuid4())
        product_id = str(uuid.uuid4())
        payload = {
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": 2}],
        }
        create_resp = client.post("/orders", json=payload)
        assert create_resp.status_code == 202
        external_id = create_resp.get_json()["external_id"]

        message = _consume_one_message(QUEUE_CREATED)
        assert message is not None, "Expected a message in the RabbitMQ queue"
        assert message["event_type"] == "OrderCreated"
        assert message["external_id"] == external_id
        assert message["customer_id"] == customer_id
        assert len(message["items"]) == 1
        assert message["items"][0]["product_id"] == product_id
        assert message["items"][0]["quantity"] == 2
