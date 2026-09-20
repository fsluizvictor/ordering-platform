"""Unit tests for the Order domain entity."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from order_service.domain.entities.order import Order, OrderStatus
from order_service.domain.exceptions import (
    InvalidOrderError,
    OrderNotDeletableError,
    OrderNotEditableError,
    OrderStatusTransitionError,
)

_CUSTOMER_ID = uuid.uuid4()
_PRODUCT_ID = uuid.uuid4()

_VALID_ITEMS = [{"product_id": str(_PRODUCT_ID), "quantity": 2}]


class TestOrderCreate:
    def test_create_with_valid_data(self) -> None:
        order = Order.create(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS)

        assert order.customer_id == _CUSTOMER_ID
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == Decimal("0")
        assert len(order.items) == 1
        assert order.items[0].product_id == _PRODUCT_ID
        assert order.items[0].quantity == 2
        assert order.items[0].unit_price == Decimal("0")
        assert order.id is not None
        assert order.external_id is not None
        assert order.created_at == order.updated_at

    def test_external_id_generated_on_creation(self) -> None:
        a = Order.create(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS)
        b = Order.create(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS)
        assert a.external_id != b.external_id

    def test_rejects_empty_items_list(self) -> None:
        with pytest.raises(InvalidOrderError, match="at least one item"):
            Order.create(customer_id=_CUSTOMER_ID, items=[])

    def test_rejects_item_with_zero_quantity(self) -> None:
        items = [{"product_id": str(_PRODUCT_ID), "quantity": 0}]
        with pytest.raises(InvalidOrderError, match="quantity"):
            Order.create(customer_id=_CUSTOMER_ID, items=items)

    def test_rejects_item_with_negative_quantity(self) -> None:
        items = [{"product_id": str(_PRODUCT_ID), "quantity": -1}]
        with pytest.raises(InvalidOrderError, match="quantity"):
            Order.create(customer_id=_CUSTOMER_ID, items=items)

    def test_rejects_item_with_invalid_product_id(self) -> None:
        items = [{"product_id": "not-a-uuid", "quantity": 1}]
        with pytest.raises(InvalidOrderError, match="product_id"):
            Order.create(customer_id=_CUSTOMER_ID, items=items)

    def test_accepts_multiple_items(self) -> None:
        items = [
            {"product_id": str(uuid.uuid4()), "quantity": 1},
            {"product_id": str(uuid.uuid4()), "quantity": 5},
        ]
        order = Order.create(customer_id=_CUSTOMER_ID, items=items)
        assert len(order.items) == 2

    def test_accepts_uuid_object_as_product_id(self) -> None:
        items = [{"product_id": _PRODUCT_ID, "quantity": 3}]
        order = Order.create(customer_id=_CUSTOMER_ID, items=items)
        assert order.items[0].product_id == _PRODUCT_ID


class TestOrderStatusTransitions:
    def _pending_order(self) -> Order:
        return Order.create(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS)

    def test_pending_to_processing(self) -> None:
        order = self._pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        assert order.status == OrderStatus.PROCESSING

    def test_processing_to_completed(self) -> None:
        order = self._pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        order.transition_to(OrderStatus.COMPLETED)
        assert order.status == OrderStatus.COMPLETED

    def test_processing_to_failed(self) -> None:
        order = self._pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        order.transition_to(OrderStatus.FAILED)
        assert order.status == OrderStatus.FAILED

    def test_pending_to_completed_is_invalid(self) -> None:
        order = self._pending_order()
        with pytest.raises(OrderStatusTransitionError):
            order.transition_to(OrderStatus.COMPLETED)

    def test_pending_to_failed_is_invalid(self) -> None:
        order = self._pending_order()
        with pytest.raises(OrderStatusTransitionError):
            order.transition_to(OrderStatus.FAILED)

    def test_completed_is_terminal(self) -> None:
        order = self._pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        order.transition_to(OrderStatus.COMPLETED)
        with pytest.raises(OrderStatusTransitionError):
            order.transition_to(OrderStatus.FAILED)

    def test_failed_is_terminal(self) -> None:
        order = self._pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        order.transition_to(OrderStatus.FAILED)
        with pytest.raises(OrderStatusTransitionError):
            order.transition_to(OrderStatus.COMPLETED)


class TestOrderEditableAndDeletable:
    def _pending_order(self) -> Order:
        return Order.create(customer_id=_CUSTOMER_ID, items=_VALID_ITEMS)

    def test_pending_order_is_editable(self) -> None:
        order = self._pending_order()
        order.assert_editable()  # Should not raise

    def test_processing_order_is_not_editable(self) -> None:
        order = self._pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        with pytest.raises(OrderNotEditableError):
            order.assert_editable()

    def test_pending_order_is_deletable(self) -> None:
        order = self._pending_order()
        order.assert_deletable()  # Should not raise

    def test_failed_order_is_deletable(self) -> None:
        order = self._pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        order.transition_to(OrderStatus.FAILED)
        order.assert_deletable()  # Should not raise

    def test_processing_order_is_not_deletable(self) -> None:
        order = self._pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        with pytest.raises(OrderNotDeletableError):
            order.assert_deletable()

    def test_completed_order_is_not_deletable(self) -> None:
        order = self._pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        order.transition_to(OrderStatus.COMPLETED)
        with pytest.raises(OrderNotDeletableError):
            order.assert_deletable()
