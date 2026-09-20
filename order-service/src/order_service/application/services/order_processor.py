"""Order Worker processing logic.

Validates Customer and Products (via cache-aside), calculates totals, and
persists the Order as COMPLETED (or FAILED for business rule violations).

This service is intentionally separate from OrderService (HTTP handler) to
keep responsibilities clear: OrderService owns the HTTP flow; OrderProcessor
owns the asynchronous processing flow.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from order_service.domain.entities.order import Order, OrderItem, OrderStatus
from order_service.domain.exceptions import OrderNotFoundError
from order_service.domain.ports.customer_lookup import CustomerLookupPort
from order_service.domain.ports.order_repository import OrderRepository
from order_service.domain.ports.product_lookup import ProductLookupPort

logger = logging.getLogger(__name__)


class _CorrelationFilter(logging.Filter):
    """Adds correlation_id and external_id to log records."""

    def __init__(self, external_id: str, correlation_id: str) -> None:
        super().__init__()
        self.external_id = external_id
        self.correlation_id = correlation_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.external_id = self.external_id  # noqa: PLE0237 — dynamically injected for log formatting
        if self.correlation_id:
            record.correlation_id = self.correlation_id  # noqa: PLE0237 — dynamically injected for log formatting
        return True


class OrderProcessor:
    """Processes an OrderCreated event through validation, pricing, and persistence."""

    def __init__(
        self,
        repository: OrderRepository,
        customer_lookup: CustomerLookupPort,
        product_lookup: ProductLookupPort,
    ) -> None:
        self._repo = repository
        self._customer_lookup = customer_lookup
        self._product_lookup = product_lookup

    def process(self, payload: dict[str, object]) -> None:
        """Process an OrderCreated event payload.

        Raises on infrastructure errors (DB, Redis, HTTP); caller should retry.
        Business validation failures (not found, insufficient stock) are
        persisted as FAILED and do NOT raise — they must be ACKed, not retried.
        """
        external_id = uuid.UUID(str(payload["external_id"]))
        customer_id = uuid.UUID(str(payload["customer_id"]))
        correlation_id = str(payload.get("correlation_id") or "")

        # Attach correlation_id and external_id to all logs from this processor.
        log_filter = _CorrelationFilter(str(external_id), correlation_id)
        logger.addFilter(log_filter)

        try:
            logger.info("Processing OrderCreated")

            order = self._repo.find_by_external_id(external_id)
            if order is None:
                raise OrderNotFoundError(f"Order not found for external_id={external_id}")

            # Idempotency: already processed by a previous Worker run.
            if order.status in (OrderStatus.COMPLETED, OrderStatus.FAILED):
                logger.info(
                    "Order already in terminal state, skipping (idempotent)",
                    extra={"status": order.status.value},
                )
                return

            # Transition to PROCESSING (idempotent if already PROCESSING from a
            # previous interrupted attempt).
            if order.status == OrderStatus.PENDING:
                order.transition_to(OrderStatus.PROCESSING)
                self._repo.update(order)
                logger.info("Order transitioned to PROCESSING")

            # --- Business validation ---

            customer = self._customer_lookup.get_customer(customer_id)
            if customer is None:
                logger.warning("Customer not found, failing order")
                self._fail_order(order)
                return

            item_prices: dict[uuid.UUID, Decimal] = {}
            for item in order.items:
                product = self._product_lookup.get_product(item.product_id)
                if product is None:
                    logger.warning(
                        "Product not found, failing order",
                        extra={"product_id": str(item.product_id)},
                    )
                    self._fail_order(order)
                    return
                if item.quantity > product.stock:
                    logger.warning(
                        "Insufficient stock, failing order",
                        extra={
                            "product_id": str(item.product_id),
                            "requested": item.quantity,
                            "available": product.stock,
                        },
                    )
                    self._fail_order(order)
                    return
                item_prices[item.product_id] = product.price

            # --- Price and total calculation ---
            self._apply_prices(order.items, item_prices)
            order.total_amount = sum(
                (item.unit_price * item.quantity for item in order.items),
                Decimal("0"),
            )

            # --- Persist COMPLETED ---
            order.transition_to(OrderStatus.COMPLETED)
            self._repo.update(order)

            logger.info(
                "Order processed successfully", extra={"total_amount": str(order.total_amount)}
            )
        finally:
            logger.removeFilter(log_filter)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _fail_order(self, order: Order) -> None:
        """Transition order to FAILED and persist. Called for business-rule failures."""
        order.transition_to(OrderStatus.FAILED)
        self._repo.update(order)

    @staticmethod
    def _apply_prices(items: list[OrderItem], prices: dict[uuid.UUID, Decimal]) -> None:
        for item in items:
            item.unit_price = prices[item.product_id]
