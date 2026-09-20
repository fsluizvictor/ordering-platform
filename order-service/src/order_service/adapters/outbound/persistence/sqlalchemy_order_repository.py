from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from order_service.adapters.outbound.persistence.models import OrderItemModel, OrderModel
from order_service.domain.entities.order import Order, OrderItem, OrderStatus
from order_service.domain.exceptions import OrderNotFoundError
from order_service.domain.ports.order_repository import OrderRepository


class SQLAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, order: Order) -> Order:
        model = _to_model(order)
        self._session.add(model)
        try:
            # Flush immediately so IntegrityError surfaces here, not at commit.
            # This allows the route to return an appropriate HTTP status code.
            self._session.flush()
        except IntegrityError:
            self._session.rollback()
            raise OrderNotFoundError(
                f"Order with external_id {order.external_id} already exists"
            ) from None
        return order

    def find_by_external_id(self, external_id: uuid.UUID) -> Order | None:
        stmt = select(OrderModel).where(OrderModel.external_id == external_id)
        model = self._session.scalar(stmt)
        return _to_entity(model) if model else None

    def find_all(self) -> list[Order]:
        stmt = select(OrderModel)
        return [_to_entity(m) for m in self._session.scalars(stmt).all()]

    def update(self, order: Order) -> Order:
        model = self._session.get(OrderModel, order.id)
        if model is None:
            raise ValueError(f"Order not found in persistence: {order.id}")
        model.status = order.status.value
        model.total_amount = order.total_amount
        model.updated_at = order.updated_at
        # Sync item unit_prices set by the Worker at processing time.
        item_map = {item.id: item for item in order.items}
        for item_model in model.items:
            domain_item = item_map.get(item_model.id)
            if domain_item is not None:
                item_model.unit_price = domain_item.unit_price
        self._session.flush()
        return order

    def delete(self, order_id: uuid.UUID) -> None:
        model = self._session.get(OrderModel, order_id)
        if model is not None:
            self._session.delete(model)
            self._session.flush()

    def count(self) -> int:
        stmt = select(func.count()).select_from(OrderModel)
        return self._session.scalar(stmt) or 0


# ── Translation helpers ────────────────────────────────────────────────────


def _to_model(order: Order) -> OrderModel:
    return OrderModel(
        id=order.id,
        external_id=order.external_id,
        customer_id=order.customer_id,
        status=order.status.value,
        total_amount=order.total_amount,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[
            OrderItemModel(
                id=item.id,
                order_id=item.order_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in order.items
        ],
    )


def _to_entity(model: OrderModel) -> Order:
    return Order(
        id=model.id,
        external_id=model.external_id,
        customer_id=model.customer_id,
        status=OrderStatus(model.status),
        total_amount=Decimal(str(model.total_amount)),
        items=[
            OrderItem(
                id=item.id,
                order_id=item.order_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=Decimal(str(item.unit_price)),
            )
            for item in model.items
        ],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
