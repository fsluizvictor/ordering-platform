"""Unit tests for the Order HTTP routes (Flask test client, mocked service)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from order_service.domain.entities.order import Order, OrderItem, OrderStatus
from order_service.domain.exceptions import (
    InvalidOrderError,
    OrderNotDeletableError,
    OrderNotFoundError,
)

_CUSTOMER_ID = uuid.uuid4()
_PRODUCT_ID = uuid.uuid4()
_EXTERNAL_ID = uuid.uuid4()


def _make_order(status: OrderStatus = OrderStatus.PENDING) -> Order:
    from datetime import UTC, datetime

    order_id = uuid.uuid4()
    return Order(
        id=order_id,
        external_id=_EXTERNAL_ID,
        customer_id=_CUSTOMER_ID,
        status=status,
        total_amount=Decimal("0"),
        items=[
            OrderItem(
                id=uuid.uuid4(),
                order_id=order_id,
                product_id=_PRODUCT_ID,
                quantity=2,
                unit_price=Decimal("0"),
            )
        ],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture()
def app():
    """Create a Flask app with a mocked service layer."""
    from flask import Flask
    from shared.correlation import init_correlation

    from order_service.adapters.inbound.http.routes import order_bp

    flask_app = Flask("test-order-service")
    init_correlation(flask_app)
    flask_app.config["SESSION_FACTORY"] = MagicMock()
    flask_app.config["RABBITMQ_URL"] = "amqp://guest:guest@localhost:5672/"
    flask_app.register_blueprint(order_bp)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def _mock_service(app, mock_svc):
    """Patch _get_service inside the routes module."""
    return patch(
        "order_service.adapters.inbound.http.routes._get_service",
        return_value=mock_svc,
    )


class TestPostOrders:
    def test_returns_202_with_external_id_on_valid_request(self, client, app) -> None:
        order = _make_order()
        svc = MagicMock()
        svc.create_order.return_value = order

        with _mock_service(app, svc):
            resp = client.post(
                "/orders",
                json={
                    "customer_id": str(_CUSTOMER_ID),
                    "items": [{"product_id": str(_PRODUCT_ID), "quantity": 2}],
                },
            )

        assert resp.status_code == 202
        data = resp.get_json()
        assert data["external_id"] == str(_EXTERNAL_ID)
        assert data["status"] == "PENDING"

    def test_returns_422_when_customer_id_missing(self, client, app) -> None:
        svc = MagicMock()
        with _mock_service(app, svc):
            resp = client.post(
                "/orders",
                json={"items": [{"product_id": str(_PRODUCT_ID), "quantity": 1}]},
            )
        assert resp.status_code == 422

    def test_returns_422_when_items_empty(self, client, app) -> None:
        svc = MagicMock()
        with _mock_service(app, svc):
            resp = client.post(
                "/orders",
                json={"customer_id": str(_CUSTOMER_ID), "items": []},
            )
        assert resp.status_code == 422

    def test_returns_422_when_quantity_is_zero(self, client, app) -> None:
        svc = MagicMock()
        with _mock_service(app, svc):
            resp = client.post(
                "/orders",
                json={
                    "customer_id": str(_CUSTOMER_ID),
                    "items": [{"product_id": str(_PRODUCT_ID), "quantity": 0}],
                },
            )
        assert resp.status_code == 422

    def test_returns_422_on_domain_validation_error(self, client, app) -> None:
        svc = MagicMock()
        svc.create_order.side_effect = InvalidOrderError("test error")
        with _mock_service(app, svc):
            resp = client.post(
                "/orders",
                json={
                    "customer_id": str(_CUSTOMER_ID),
                    "items": [{"product_id": str(_PRODUCT_ID), "quantity": 1}],
                },
            )
        assert resp.status_code == 422

    def test_returns_422_when_customer_id_not_uuid(self, client, app) -> None:
        svc = MagicMock()
        with _mock_service(app, svc):
            resp = client.post(
                "/orders",
                json={
                    "customer_id": "not-a-uuid",
                    "items": [{"product_id": str(_PRODUCT_ID), "quantity": 1}],
                },
            )
        assert resp.status_code == 422


class TestGetOrders:
    def test_returns_200_with_list(self, client, app) -> None:
        svc = MagicMock()
        svc.list_orders.return_value = [_make_order()]
        with _mock_service(app, svc):
            resp = client.get("/orders")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)
        assert len(resp.get_json()) == 1

    def test_count_returns_total(self, client, app) -> None:
        svc = MagicMock()
        svc.count_orders.return_value = 7
        with _mock_service(app, svc):
            resp = client.get("/orders/count")
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 7

    def test_get_by_external_id_returns_order(self, client, app) -> None:
        order = _make_order()
        svc = MagicMock()
        svc.get_order.return_value = order
        with _mock_service(app, svc):
            resp = client.get(f"/orders/{_EXTERNAL_ID}")
        assert resp.status_code == 200
        assert resp.get_json()["external_id"] == str(_EXTERNAL_ID)

    def test_get_by_external_id_returns_404_when_not_found(self, client, app) -> None:
        svc = MagicMock()
        svc.get_order.side_effect = OrderNotFoundError("not found")
        with _mock_service(app, svc):
            resp = client.get(f"/orders/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestDeleteOrder:
    def test_delete_returns_204_on_success(self, client, app) -> None:
        svc = MagicMock()
        svc.delete_order.return_value = None
        with _mock_service(app, svc):
            resp = client.delete(f"/orders/{_EXTERNAL_ID}")
        assert resp.status_code == 204

    def test_delete_returns_404_when_not_found(self, client, app) -> None:
        svc = MagicMock()
        svc.delete_order.side_effect = OrderNotFoundError("not found")
        with _mock_service(app, svc):
            resp = client.delete(f"/orders/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_delete_returns_422_when_not_deletable(self, client, app) -> None:
        svc = MagicMock()
        svc.delete_order.side_effect = OrderNotDeletableError("not deletable")
        with _mock_service(app, svc):
            resp = client.delete(f"/orders/{_EXTERNAL_ID}")
        assert resp.status_code == 422
