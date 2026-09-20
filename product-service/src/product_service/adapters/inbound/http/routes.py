from __future__ import annotations

import uuid

from flask import Blueprint, g, jsonify, request
from shared.errors import error_response

from product_service.adapters.outbound.persistence.sqlalchemy_product_repository import (
    SQLAlchemyProductRepository,
)
from product_service.application.services.product_service import ProductService
from product_service.domain.entities.product import Product
from product_service.domain.exceptions import (
    InvalidProductDataError,
    ProductNotFoundError,
)

product_bp = Blueprint("products", __name__)


def _get_service() -> ProductService:
    """Return a ProductService wired to the request-scoped DB session."""
    from flask import current_app

    if "db_session" not in g:
        factory = current_app.config["SESSION_FACTORY"]
        g.db_session = factory()
    repo = SQLAlchemyProductRepository(g.db_session)
    return ProductService(repo)


def _serialize(product: Product) -> dict[str, object]:
    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description,
        "price": float(product.price),
        "stock": product.stock,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
    }


@product_bp.post("/products")
def create_product() -> tuple:
    data: dict = request.get_json(silent=True) or {}
    name: str = data.get("name") or ""
    price = data.get("price")
    stock = data.get("stock")
    description: str = data.get("description") or ""

    if not name or price is None or stock is None:
        return error_response("VALIDATION_ERROR", "name, price and stock are required", 422)

    if not isinstance(stock, int) or isinstance(stock, bool):
        return error_response("VALIDATION_ERROR", "stock must be an integer", 422)

    try:
        product = _get_service().create_product(
            name=name, price=price, stock=stock, description=description
        )
        return jsonify(_serialize(product)), 201
    except InvalidProductDataError as exc:
        return error_response("VALIDATION_ERROR", str(exc), 422)


@product_bp.get("/products")
def list_products() -> tuple:
    products = _get_service().list_products()
    return jsonify([_serialize(p) for p in products]), 200


@product_bp.get("/products/count")
def count_products() -> tuple:
    total = _get_service().count_products()
    return jsonify({"count": total}), 200


@product_bp.get("/products/name/<string:name>")
def find_by_name(name: str) -> tuple:
    products = _get_service().find_by_name(name)
    return jsonify([_serialize(p) for p in products]), 200


@product_bp.get("/products/<uuid:product_id>")
def get_product(product_id: uuid.UUID) -> tuple:
    try:
        product = _get_service().get_product(product_id)
        return jsonify(_serialize(product)), 200
    except ProductNotFoundError:
        return error_response("PRODUCT_NOT_FOUND", "Product not found", 404)


@product_bp.put("/products/<uuid:product_id>")
def update_product(product_id: uuid.UUID) -> tuple:
    data: dict = request.get_json(silent=True) or {}
    kwargs: dict = {}
    for field in ("name", "price", "stock", "description"):
        if field in data:
            kwargs[field] = data[field]

    if not kwargs:
        return error_response("VALIDATION_ERROR", "No updatable fields provided", 422)

    if "stock" in kwargs:
        stock = kwargs["stock"]
        if not isinstance(stock, int) or isinstance(stock, bool):
            return error_response("VALIDATION_ERROR", "stock must be an integer", 422)

    try:
        product = _get_service().update_product(product_id, **kwargs)
        return jsonify(_serialize(product)), 200
    except ProductNotFoundError:
        return error_response("PRODUCT_NOT_FOUND", "Product not found", 404)
    except InvalidProductDataError as exc:
        return error_response("VALIDATION_ERROR", str(exc), 422)


@product_bp.delete("/products/<uuid:product_id>")
def delete_product(product_id: uuid.UUID) -> tuple:
    try:
        _get_service().delete_product(product_id)
        return "", 204
    except ProductNotFoundError:
        return error_response("PRODUCT_NOT_FOUND", "Product not found", 404)
