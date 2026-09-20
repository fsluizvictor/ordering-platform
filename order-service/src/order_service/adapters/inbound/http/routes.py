from __future__ import annotations

import logging
import uuid

from flask import Blueprint, g, jsonify, request
from shared.errors import error_response

from order_service.adapters.outbound.messaging.rabbitmq_publisher import (
    RabbitMQOrderPublisher,
)
from order_service.adapters.outbound.persistence.sqlalchemy_order_repository import (
    SQLAlchemyOrderRepository,
)
from order_service.application.services.order_service import OrderService
from order_service.domain.entities.order import Order
from order_service.domain.exceptions import (
    InvalidOrderError,
    OrderNotDeletableError,
    OrderNotFoundError,
)

order_bp = Blueprint("orders", __name__)
logger = logging.getLogger(__name__)


def _get_service() -> OrderService:
    """Return an OrderService wired to the request-scoped DB session."""
    from flask import current_app

    if "db_session" not in g:
        factory = current_app.config["SESSION_FACTORY"]
        g.db_session = factory()

    rabbitmq_url: str = current_app.config["RABBITMQ_URL"]
    repo = SQLAlchemyOrderRepository(g.db_session)
    publisher = RabbitMQOrderPublisher(rabbitmq_url)
    return OrderService(repo, publisher)


def _serialize(order: Order) -> dict[str, object]:
    return {
        "id": str(order.id),
        "external_id": str(order.external_id),
        "customer_id": str(order.customer_id),
        "status": order.status.value,
        "total_amount": str(order.total_amount),
        "items": [
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
            }
            for item in order.items
        ],
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
    }


@order_bp.post("/orders")
def create_order() -> tuple:
    data: dict = request.get_json(silent=True) or {}

    customer_id_raw = data.get("customer_id")
    if not customer_id_raw:
        return error_response("VALIDATION_ERROR", "customer_id is required", 422)
    try:
        customer_id = uuid.UUID(str(customer_id_raw))
    except ValueError:
        return error_response("VALIDATION_ERROR", "customer_id must be a valid UUID", 422)

    items_raw = data.get("items")
    if not isinstance(items_raw, list) or len(items_raw) == 0:
        return error_response("VALIDATION_ERROR", "items must be a non-empty list", 422)

    for i, item in enumerate(items_raw):
        if not isinstance(item, dict):
            return error_response("VALIDATION_ERROR", f"items[{i}] must be an object", 422)
        if not item.get("product_id"):
            return error_response("VALIDATION_ERROR", f"items[{i}].product_id is required", 422)
        if not isinstance(item.get("quantity"), int) or item["quantity"] <= 0:
            return error_response(
                "VALIDATION_ERROR",
                f"items[{i}].quantity must be a positive integer",
                422,
            )

    correlation_id: uuid.UUID | None = None
    raw_cid = getattr(g, "correlation_id", None)
    if raw_cid:
        try:
            correlation_id = uuid.UUID(str(raw_cid))
        except ValueError:
            pass

    log_extra = {
        "customer_id": str(customer_id),
        "item_count": len(items_raw),
    }
    if correlation_id:
        log_extra["correlation_id"] = str(correlation_id)

    logger.info("POST /orders request received", extra=log_extra)

    try:
        order = _get_service().create_order(
            customer_id=customer_id,
            items=items_raw,
            correlation_id=correlation_id,
        )
        logger.info(
            "Order creation successful",
            extra={
                "external_id": str(order.external_id),
                "correlation_id": str(correlation_id) if correlation_id else None,
            },
        )
        return jsonify({"external_id": str(order.external_id), "status": order.status.value}), 202
    except InvalidOrderError as exc:
        return error_response("VALIDATION_ERROR", str(exc), 422)
    except Exception:
        return error_response("INTERNAL_ERROR", "Failed to create order", 500)


@order_bp.get("/orders")
def list_orders() -> tuple:
    orders = _get_service().list_orders()
    return jsonify([_serialize(o) for o in orders]), 200


# Must be registered before /<uuid> to prevent Flask from trying to parse "count" as UUID.
@order_bp.get("/orders/count")
def count_orders() -> tuple:
    total = _get_service().count_orders()
    return jsonify({"count": total}), 200


@order_bp.get("/orders/<uuid:external_id>")
def get_order(external_id: uuid.UUID) -> tuple:
    try:
        order = _get_service().get_order(external_id)
        return jsonify(_serialize(order)), 200
    except OrderNotFoundError:
        return error_response("ORDER_NOT_FOUND", "Order not found", 404)


@order_bp.delete("/orders/<uuid:external_id>")
def delete_order(external_id: uuid.UUID) -> tuple:
    try:
        _get_service().delete_order(external_id)
        return "", 204
    except OrderNotFoundError:
        return error_response("ORDER_NOT_FOUND", "Order not found", 404)
    except OrderNotDeletableError as exc:
        return error_response("ORDER_NOT_DELETABLE", str(exc), 422)
