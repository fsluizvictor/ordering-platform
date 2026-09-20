from __future__ import annotations

import uuid

from flask import Blueprint, g, jsonify, request
from shared.errors import error_response

from customer_service.adapters.outbound.persistence.sqlalchemy_customer_repository import (
    SQLAlchemyCustomerRepository,
)
from customer_service.application.services.customer_service import CustomerService
from customer_service.domain.entities.customer import Customer
from customer_service.domain.exceptions import (
    CustomerEmailAlreadyExistsError,
    CustomerNotFoundError,
    InvalidCustomerDataError,
)

customer_bp = Blueprint("customers", __name__)


def _get_service() -> CustomerService:
    """Return a CustomerService wired to the request-scoped DB session."""
    from flask import current_app

    if "db_session" not in g:
        factory = current_app.config["SESSION_FACTORY"]
        g.db_session = factory()
    repo = SQLAlchemyCustomerRepository(g.db_session)
    return CustomerService(repo)


def _serialize(customer: Customer) -> dict[str, object]:
    return {
        "id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "created_at": customer.created_at.isoformat(),
        "updated_at": customer.updated_at.isoformat(),
    }


@customer_bp.post("/customers")
def create_customer() -> tuple:
    data: dict = request.get_json(silent=True) or {}
    name: str = data.get("name") or ""
    email: str = data.get("email") or ""
    phone: str = data.get("phone") or ""

    if not name or not email:
        return error_response("VALIDATION_ERROR", "name and email are required", 422)

    try:
        customer = _get_service().create_customer(name=name, email=email, phone=phone)
        return jsonify(_serialize(customer)), 201
    except InvalidCustomerDataError as exc:
        return error_response("VALIDATION_ERROR", str(exc), 422)
    except CustomerEmailAlreadyExistsError:
        return error_response("EMAIL_ALREADY_EXISTS", "Email already exists", 409)


@customer_bp.get("/customers")
def list_customers() -> tuple:
    customers = _get_service().list_customers()
    return jsonify([_serialize(c) for c in customers]), 200


# Must be registered before /<uuid:customer_id> so Flask routes "count" as
# a static path segment, not a UUID. Flask already gives priority to static
# segments over converters, but explicit ordering communicates intent.
@customer_bp.get("/customers/count")
def count_customers() -> tuple:
    total = _get_service().count_customers()
    return jsonify({"count": total}), 200


@customer_bp.get("/customers/name/<string:name>")
def find_by_name(name: str) -> tuple:
    customers = _get_service().find_by_name(name)
    return jsonify([_serialize(c) for c in customers]), 200


@customer_bp.get("/customers/<uuid:customer_id>")
def get_customer(customer_id: uuid.UUID) -> tuple:
    try:
        customer = _get_service().get_customer(customer_id)
        return jsonify(_serialize(customer)), 200
    except CustomerNotFoundError:
        return error_response("CUSTOMER_NOT_FOUND", "Customer not found", 404)


@customer_bp.put("/customers/<uuid:customer_id>")
def update_customer(customer_id: uuid.UUID) -> tuple:
    data: dict = request.get_json(silent=True) or {}
    kwargs: dict[str, str | None] = {}
    for field in ("name", "email", "phone"):
        if field in data:
            kwargs[field] = data[field]

    if not kwargs:
        return error_response("VALIDATION_ERROR", "No updatable fields provided", 422)

    try:
        customer = _get_service().update_customer(customer_id, **kwargs)
        return jsonify(_serialize(customer)), 200
    except CustomerNotFoundError:
        return error_response("CUSTOMER_NOT_FOUND", "Customer not found", 404)
    except CustomerEmailAlreadyExistsError:
        return error_response("EMAIL_ALREADY_EXISTS", "Email already exists", 409)
    except InvalidCustomerDataError as exc:
        return error_response("VALIDATION_ERROR", str(exc), 422)


@customer_bp.delete("/customers/<uuid:customer_id>")
def delete_customer(customer_id: uuid.UUID) -> tuple:
    try:
        _get_service().delete_customer(customer_id)
        return "", 204
    except CustomerNotFoundError:
        return error_response("CUSTOMER_NOT_FOUND", "Customer not found", 404)
