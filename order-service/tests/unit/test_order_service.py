"""Unit tests for the OrderService application service."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from order_service.application.services.order_service import OrderService
from order_service.domain.entities.order import Order, OrderStatus
from order_service.domain.exceptions import (
    InvalidOrderError,
    OrderNotDeletableError,
    OrderNotFoundError,
)
from order_service.domain.ports.order_publisher import OrderCreatedEvent, OrderPublisher
from order_service.domain.ports.order_repository import OrderRepository

_CUSTOMER_ID = uuid.uuid4()
_PRODUCT_ID = uuid.uuid4()
_VALID_ITEMS = [{"product_id": str(_PRODUCT_ID), "quantity": 2}]


def _make_service(
    repo: OrderRepository | None = None,
    publisher: OrderPublisher | None = None,
) -> OrderService:
    repo = repo or MagicMock(spec=OrderRepository)
    publisher = publisher or MagicMock(spec=OrderPublisher)
    return OrderService(repo, publisher)


def _make_pending_order() -> Order:
    return Order.create(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS)


class TestCreateOrder:
    def test_persists_before_publishing(self) -> None:
        """Persist-then-publish order (ADR-011)."""
        call_order: list[str] = []
        repo = MagicMock(spec=OrderRepository)
        publisher = MagicMock(spec=OrderPublisher)

        def fake_save(order: Order) -> Order:
            call_order.append("save")
            return order

        def fake_publish(event: OrderCreatedEvent) -> None:
            call_order.append("publish")

        repo.save.side_effect = fake_save
        publisher.publish_order_created.side_effect = fake_publish

        svc = OrderService(repo, publisher)
        svc.create_order(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS)

        assert call_order == ["save", "publish"], "Must persist before publishing"

    def test_returns_order_with_pending_status(self) -> None:
        repo = MagicMock(spec=OrderRepository)
        repo.save.side_effect = lambda o: o
        svc = _make_service(repo=repo)

        order = svc.create_order(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS)

        assert order.status == OrderStatus.PENDING

    def test_event_has_event_id_and_occurred_at(self) -> None:
        repo = MagicMock(spec=OrderRepository)
        repo.save.side_effect = lambda o: o
        publisher = MagicMock(spec=OrderPublisher)
        svc = OrderService(repo, publisher)

        svc.create_order(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS)

        publisher.publish_order_created.assert_called_once()
        event: OrderCreatedEvent = publisher.publish_order_created.call_args[0][0]
        assert event.event_id is not None
        assert event.occurred_at is not None
        assert event.event_type == "OrderCreated"

    def test_correlation_id_propagated_to_event(self) -> None:
        repo = MagicMock(spec=OrderRepository)
        repo.save.side_effect = lambda o: o
        publisher = MagicMock(spec=OrderPublisher)
        svc = OrderService(repo, publisher)
        cid = uuid.uuid4()

        svc.create_order(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS, correlation_id=cid)

        event: OrderCreatedEvent = publisher.publish_order_created.call_args[0][0]
        assert event.correlation_id == cid

    def test_rejects_empty_items_via_domain(self) -> None:
        svc = _make_service()
        with pytest.raises(InvalidOrderError):
            svc.create_order(customer_id=_CUSTOMER_ID, items=[])

    def test_rejects_zero_quantity_via_domain(self) -> None:
        svc = _make_service()
        with pytest.raises(InvalidOrderError):
            svc.create_order(
                customer_id=_CUSTOMER_ID,
                items=[{"product_id": str(_PRODUCT_ID), "quantity": 0}],
            )


class TestGetOrder:
    def test_returns_order_when_found(self) -> None:
        order = _make_pending_order()
        repo = MagicMock(spec=OrderRepository)
        repo.find_by_external_id.return_value = order
        svc = _make_service(repo=repo)

        result = svc.get_order(order.external_id)

        assert result == order

    def test_raises_when_not_found(self) -> None:
        repo = MagicMock(spec=OrderRepository)
        repo.find_by_external_id.return_value = None
        svc = _make_service(repo=repo)

        with pytest.raises(OrderNotFoundError):
            svc.get_order(uuid.uuid4())


class TestDeleteOrder:
    def test_deletes_pending_order(self) -> None:
        order = _make_pending_order()
        repo = MagicMock(spec=OrderRepository)
        repo.find_by_external_id.return_value = order
        svc = _make_service(repo=repo)

        svc.delete_order(order.external_id)

        repo.delete.assert_called_once_with(order.id)

    def test_raises_when_not_found(self) -> None:
        repo = MagicMock(spec=OrderRepository)
        repo.find_by_external_id.return_value = None
        svc = _make_service(repo=repo)

        with pytest.raises(OrderNotFoundError):
            svc.delete_order(uuid.uuid4())

    def test_raises_when_order_is_processing(self) -> None:
        from order_service.domain.entities.order import OrderStatus

        order = _make_pending_order()
        order.status = OrderStatus.PROCESSING
        repo = MagicMock(spec=OrderRepository)
        repo.find_by_external_id.return_value = order
        svc = _make_service(repo=repo)

        with pytest.raises(OrderNotDeletableError):
            svc.delete_order(order.external_id)
