from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from order_service.domain.entities.order import Order
from order_service.domain.exceptions import OrderNotFoundError
from order_service.domain.ports.order_publisher import (
    OrderCreatedEvent,
    OrderItemPayload,
    OrderPublisher,
)
from order_service.domain.ports.order_repository import OrderRepository

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        publisher: OrderPublisher,
    ) -> None:
        self._repo = repository
        self._publisher = publisher

    def create_order(
        self,
        customer_id: uuid.UUID,
        items: list[dict[str, object]],
        correlation_id: uuid.UUID | None = None,
    ) -> Order:
        """Validate, persist as PENDING, publish OrderCreated, and return the Order.

        Persists before publishing (ADR-011): if the publish step fails the
        record remains PENDING and can be recovered.  The Worker processes the
        existing PENDING record — it does not re-create it.
        """
        order = Order.create(customer_id=customer_id, items=items)

        # Persist first so GET /orders/{external_id} works immediately.
        saved = self._repo.save(order)
        logger.info(
            "Order persisted as PENDING",
            extra={"order_id": str(saved.id), "external_id": str(saved.external_id)},
        )

        event = OrderCreatedEvent(
            event_id=uuid.uuid4(),
            event_type="OrderCreated",
            occurred_at=datetime.now(UTC),
            correlation_id=correlation_id,
            external_id=saved.external_id,
            customer_id=saved.customer_id,
            items=[
                OrderItemPayload(
                    product_id=item.product_id,
                    quantity=item.quantity,
                )
                for item in saved.items
            ],
        )
        self._publisher.publish_order_created(event)
        logger.info(
            "OrderCreated published",
            extra={
                "event_id": str(event.event_id),
                "external_id": str(saved.external_id),
            },
        )

        return saved

    def get_order(self, external_id: uuid.UUID) -> Order:
        order = self._repo.find_by_external_id(external_id)
        if order is None:
            raise OrderNotFoundError(str(external_id))
        return order

    def list_orders(self) -> list[Order]:
        return self._repo.find_all()

    def count_orders(self) -> int:
        return self._repo.count()

    def delete_order(self, external_id: uuid.UUID) -> None:
        """Delete an order. Only PENDING or FAILED orders can be deleted."""
        order = self._repo.find_by_external_id(external_id)
        if order is None:
            raise OrderNotFoundError(str(external_id))
        order.assert_deletable()
        self._repo.delete(order.id)
        logger.info("Order deleted", extra={"external_id": str(external_id)})
