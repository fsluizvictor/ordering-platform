"""Unit tests for OrderProcessor.

All external dependencies are replaced with mocks/fakes so these tests
run without a database, Redis, or network.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from order_service.application.services.order_processor import OrderProcessor
from order_service.domain.entities.order import Order, OrderStatus
from order_service.domain.exceptions import OrderNotFoundError
from order_service.domain.ports.customer_lookup import CustomerData, CustomerLookupPort
from order_service.domain.ports.order_repository import OrderRepository
from order_service.domain.ports.product_lookup import ProductData, ProductLookupPort

# ── Fixtures ──────────────────────────────────────────────────────────────────

_CUSTOMER_ID = uuid.uuid4()
_PRODUCT_ID = uuid.uuid4()
_PRODUCT_ID_2 = uuid.uuid4()

_VALID_CUSTOMER = CustomerData(id=_CUSTOMER_ID, name="Alice", email="alice@example.com")
_VALID_PRODUCT = ProductData(id=_PRODUCT_ID, name="Widget", price=Decimal("10.00"), stock=100)
_VALID_PRODUCT_2 = ProductData(id=_PRODUCT_ID_2, name="Gadget", price=Decimal("5.50"), stock=50)


def _make_pending_order(
    customer_id: uuid.UUID = _CUSTOMER_ID,
    items: list[dict[str, object]] | None = None,
) -> Order:
    return Order.create(
        customer_id=customer_id,
        items=items or [{"product_id": str(_PRODUCT_ID), "quantity": 2}],
    )


def _make_processor(
    order: Order | None = None,
    customer: CustomerData | None = _VALID_CUSTOMER,
    product: ProductData | None = _VALID_PRODUCT,
) -> tuple[OrderProcessor, MagicMock]:
    repo = MagicMock(spec=OrderRepository)
    repo.find_by_external_id.return_value = order
    repo.update.return_value = order

    customer_lookup = MagicMock(spec=CustomerLookupPort)
    customer_lookup.get_customer.return_value = customer

    product_lookup = MagicMock(spec=ProductLookupPort)
    product_lookup.get_product.return_value = product

    return OrderProcessor(repo, customer_lookup, product_lookup), repo


def _make_payload(order: Order) -> dict[str, object]:
    return {
        "external_id": str(order.external_id),
        "customer_id": str(order.customer_id),
        "items": [{"product_id": str(i.product_id), "quantity": i.quantity} for i in order.items],
        "event_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
    }


# ── Happy path ────────────────────────────────────────────────────────────────


class TestOrderProcessorHappyPath:
    def test_order_completed_on_success(self) -> None:
        order = _make_pending_order()
        processor, repo = _make_processor(order=order)

        processor.process(_make_payload(order))

        # update() called twice: once at PROCESSING, once at COMPLETED.
        assert repo.update.call_count == 2
        assert order.status == OrderStatus.COMPLETED

    def test_total_amount_calculated_correctly(self) -> None:
        """2 × £10.00 = £20.00."""
        order = _make_pending_order(items=[{"product_id": str(_PRODUCT_ID), "quantity": 2}])
        processor, _ = _make_processor(order=order)

        processor.process(_make_payload(order))

        assert order.total_amount == Decimal("20.00")

    def test_unit_price_set_on_each_item(self) -> None:
        order = _make_pending_order()
        processor, _ = _make_processor(order=order)

        processor.process(_make_payload(order))

        assert order.items[0].unit_price == Decimal("10.00")

    def test_total_amount_with_multiple_items(self) -> None:
        """2 × £10.00 + 3 × £5.50 = £36.50."""
        order = _make_pending_order(
            items=[
                {"product_id": str(_PRODUCT_ID), "quantity": 2},
                {"product_id": str(_PRODUCT_ID_2), "quantity": 3},
            ]
        )

        repo = MagicMock(spec=OrderRepository)
        repo.find_by_external_id.return_value = order
        repo.update.return_value = order

        customer_lookup = MagicMock(spec=CustomerLookupPort)
        customer_lookup.get_customer.return_value = _VALID_CUSTOMER

        product_lookup = MagicMock(spec=ProductLookupPort)
        product_lookup.get_product.side_effect = lambda pid: (
            _VALID_PRODUCT if pid == _PRODUCT_ID else _VALID_PRODUCT_2
        )

        processor = OrderProcessor(repo, customer_lookup, product_lookup)
        processor.process(_make_payload(order))

        assert order.total_amount == Decimal("36.50")


# ── Business validation failures ──────────────────────────────────────────────


class TestOrderProcessorValidationFailures:
    def test_customer_not_found_sets_failed_status(self) -> None:
        order = _make_pending_order()
        processor, repo = _make_processor(order=order, customer=None)

        processor.process(_make_payload(order))

        assert order.status == OrderStatus.FAILED

    def test_customer_not_found_does_not_raise(self) -> None:
        """Business failures must be ACKed; they should not propagate as exceptions."""
        order = _make_pending_order()
        processor, _ = _make_processor(order=order, customer=None)

        # No exception expected.
        processor.process(_make_payload(order))

    def test_product_not_found_sets_failed_status(self) -> None:
        order = _make_pending_order()
        processor, _ = _make_processor(order=order, product=None)

        processor.process(_make_payload(order))

        assert order.status == OrderStatus.FAILED

    def test_insufficient_stock_sets_failed_status(self) -> None:
        # Product stock is 1, but order requests 5.
        low_stock = ProductData(id=_PRODUCT_ID, name="Widget", price=Decimal("10.00"), stock=1)
        order = _make_pending_order(items=[{"product_id": str(_PRODUCT_ID), "quantity": 5}])
        processor, _ = _make_processor(order=order, product=low_stock)

        processor.process(_make_payload(order))

        assert order.status == OrderStatus.FAILED

    def test_order_not_found_raises(self) -> None:
        processor, _ = _make_processor(order=None)
        order = _make_pending_order()

        with pytest.raises(OrderNotFoundError):
            processor.process(_make_payload(order))


# ── Idempotency ───────────────────────────────────────────────────────────────


class TestOrderProcessorIdempotency:
    def _completed_order(self) -> Order:
        order = _make_pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        order.transition_to(OrderStatus.COMPLETED)
        return order

    def _failed_order(self) -> Order:
        order = _make_pending_order()
        order.transition_to(OrderStatus.PROCESSING)
        order.transition_to(OrderStatus.FAILED)
        return order

    def test_completed_order_is_skipped(self) -> None:
        order = self._completed_order()
        processor, repo = _make_processor(order=order)

        processor.process(_make_payload(order))

        # No update should be called for an already-terminal order.
        repo.update.assert_not_called()

    def test_failed_order_is_skipped(self) -> None:
        order = self._failed_order()
        processor, repo = _make_processor(order=order)

        processor.process(_make_payload(order))

        repo.update.assert_not_called()

    def test_processing_order_resumes_without_transition_error(self) -> None:
        """An order stuck in PROCESSING (from a crashed Worker) is re-processed."""
        order = _make_pending_order()
        order.transition_to(OrderStatus.PROCESSING)  # Simulate interrupted Worker.

        processor, repo = _make_processor(order=order)
        processor.process(_make_payload(order))

        # Should reach COMPLETED without raising.
        assert order.status == OrderStatus.COMPLETED
