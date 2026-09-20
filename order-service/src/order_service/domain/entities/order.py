from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from order_service.domain.exceptions import (
    InvalidOrderError,
    OrderNotDeletableError,
    OrderNotEditableError,
    OrderStatusTransitionError,
)


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Valid status transitions enforced at domain level.
_VALID_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.PROCESSING}),
    OrderStatus.PROCESSING: frozenset({OrderStatus.COMPLETED, OrderStatus.FAILED}),
    OrderStatus.COMPLETED: frozenset(),
    OrderStatus.FAILED: frozenset(),
}

# Statuses in which an order may be deleted.
_DELETABLE_STATUSES: frozenset[OrderStatus] = frozenset({OrderStatus.PENDING, OrderStatus.FAILED})


@dataclass
class OrderItem:
    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    # Filled by the Worker at processing time; zero at creation.
    unit_price: Decimal = field(default=Decimal("0"))


@dataclass
class Order:
    id: uuid.UUID
    external_id: uuid.UUID
    customer_id: uuid.UUID
    status: OrderStatus
    # Filled by the Worker after validating prices; zero at creation.
    total_amount: Decimal
    items: list[OrderItem]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        customer_id: uuid.UUID,
        items: list[dict[str, object]],
    ) -> Order:
        """Validate and construct a new PENDING Order.

        *items* is a list of dicts with keys ``product_id`` (str | UUID)
        and ``quantity`` (int).  Domain invariants are enforced here so
        the entity is always valid once constructed.
        """
        if not items:
            raise InvalidOrderError("Order must contain at least one item")

        order_id = uuid.uuid4()
        now = datetime.now(UTC)
        external_id = uuid.uuid4()

        order_items: list[OrderItem] = []
        for raw in items:
            quantity = raw.get("quantity")
            if not isinstance(quantity, int) or quantity <= 0:
                raise InvalidOrderError(
                    f"Item quantity must be a positive integer, got: {quantity!r}"
                )
            product_id_raw = raw.get("product_id")
            try:
                product_id = (
                    product_id_raw
                    if isinstance(product_id_raw, uuid.UUID)
                    else uuid.UUID(str(product_id_raw))
                )
            except (ValueError, AttributeError) as exc:
                raise InvalidOrderError(f"Invalid product_id: {product_id_raw!r}") from exc

            order_items.append(
                OrderItem(
                    id=uuid.uuid4(),
                    order_id=order_id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=Decimal("0"),
                )
            )

        return cls(
            id=order_id,
            external_id=external_id,
            customer_id=customer_id,
            status=OrderStatus.PENDING,
            total_amount=Decimal("0"),
            items=order_items,
            created_at=now,
            updated_at=now,
        )

    def transition_to(self, new_status: OrderStatus) -> None:
        """Apply a status transition, enforcing the allowed state machine."""
        allowed = _VALID_TRANSITIONS.get(self.status, frozenset())
        if new_status not in allowed:
            raise OrderStatusTransitionError(
                f"Cannot transition from {self.status.value} to {new_status.value}"
            )
        self.status = new_status
        self.updated_at = datetime.now(UTC)

    def assert_editable(self) -> None:
        """Raise OrderNotEditableError if the order cannot be modified."""
        if self.status is not OrderStatus.PENDING:
            raise OrderNotEditableError(
                f"Order can only be modified when PENDING, current status: {self.status.value}"
            )

    def assert_deletable(self) -> None:
        """Raise OrderNotDeletableError if the order cannot be deleted."""
        if self.status not in _DELETABLE_STATUSES:
            raise OrderNotDeletableError(f"Order cannot be deleted in status: {self.status.value}")
