"""Unit tests for Customer HTTP routes — CustomerService is mocked."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

from customer_service.adapters.inbound.http.app import create_app
from customer_service.application.services.customer_service import CustomerService
from customer_service.domain.entities.customer import Customer
from customer_service.domain.exceptions import (
    CustomerEmailAlreadyExistsError,
    CustomerNotFoundError,
    InvalidCustomerDataError,
)


def _make_customer(**overrides: object) -> Customer:
    defaults: dict = {
        "id": uuid.uuid4(),
        "name": "Alice",
        "email": "alice@example.com",
        "phone": "123",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Customer(**defaults)


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock(spec=CustomerService)


@pytest.fixture
def client(mock_service: MagicMock) -> Generator[tuple[FlaskClient, MagicMock], None, None]:
    # Patch _get_service so routes receive the mock — no DB involved.
    with patch(
        "customer_service.adapters.inbound.http.routes._get_service",
        return_value=mock_service,
    ):
        app = create_app(session_factory=MagicMock())
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c, mock_service


# ---------------------------------------------------------------------------
# POST /customers
# ---------------------------------------------------------------------------


class TestPostCustomers:
    def test_201_on_valid_request(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        customer = _make_customer()
        svc.create_customer.return_value = customer

        resp = c.post("/customers", json={"name": "Alice", "email": "alice@example.com"})

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["email"] == "alice@example.com"
        assert "id" in data
        assert "created_at" in data

    def test_422_when_name_is_missing(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, _ = client
        resp = c.post("/customers", json={"email": "x@example.com"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_422_when_email_is_missing(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, _ = client
        resp = c.post("/customers", json={"name": "Alice"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_422_when_domain_rejects_data(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.create_customer.side_effect = InvalidCustomerDataError("name cannot be empty")

        resp = c.post("/customers", json={"name": " ", "email": "x@example.com"})

        # Route detects empty name early (before calling service), so 422 from route guard.
        assert resp.status_code == 422

    def test_409_on_duplicate_email(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.create_customer.side_effect = CustomerEmailAlreadyExistsError("taken")

        resp = c.post("/customers", json={"name": "Alice", "email": "alice@example.com"})

        assert resp.status_code == 409
        assert resp.get_json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


# ---------------------------------------------------------------------------
# GET /customers
# ---------------------------------------------------------------------------


class TestGetCustomers:
    def test_200_returns_list(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.list_customers.return_value = [_make_customer(), _make_customer()]

        resp = c.get("/customers")

        assert resp.status_code == 200
        assert len(resp.get_json()) == 2

    def test_200_returns_empty_list(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.list_customers.return_value = []

        resp = c.get("/customers")

        assert resp.status_code == 200
        assert resp.get_json() == []


# ---------------------------------------------------------------------------
# GET /customers/count
# ---------------------------------------------------------------------------


class TestGetCustomersCount:
    def test_200_returns_count(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.count_customers.return_value = 7

        resp = c.get("/customers/count")

        assert resp.status_code == 200
        assert resp.get_json() == {"count": 7}


# ---------------------------------------------------------------------------
# GET /customers/name/<name>
# ---------------------------------------------------------------------------


class TestGetCustomersByName:
    def test_200_returns_matching_customers(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.find_by_name.return_value = [_make_customer(name="Alice")]

        resp = c.get("/customers/name/Alice")

        assert resp.status_code == 200
        assert resp.get_json()[0]["name"] == "Alice"
        svc.find_by_name.assert_called_once_with("Alice")


# ---------------------------------------------------------------------------
# GET /customers/<id>
# ---------------------------------------------------------------------------


class TestGetCustomerById:
    def test_200_when_found(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        customer = _make_customer()
        svc.get_customer.return_value = customer

        resp = c.get(f"/customers/{customer.id}")

        assert resp.status_code == 200
        assert resp.get_json()["id"] == str(customer.id)

    def test_404_when_not_found(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.get_customer.side_effect = CustomerNotFoundError("x")

        resp = c.get(f"/customers/{uuid.uuid4()}")

        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


# ---------------------------------------------------------------------------
# PUT /customers/<id>
# ---------------------------------------------------------------------------


class TestPutCustomer:
    def test_200_on_valid_update(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        customer = _make_customer(name="Updated")
        svc.update_customer.return_value = customer

        resp = c.put(f"/customers/{customer.id}", json={"name": "Updated"})

        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Updated"

    def test_404_when_not_found(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.update_customer.side_effect = CustomerNotFoundError("x")

        resp = c.put(f"/customers/{uuid.uuid4()}", json={"name": "New"})

        assert resp.status_code == 404

    def test_409_on_duplicate_email(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.update_customer.side_effect = CustomerEmailAlreadyExistsError("taken")

        resp = c.put(
            f"/customers/{uuid.uuid4()}",
            json={"email": "taken@example.com"},
        )

        assert resp.status_code == 409

    def test_422_on_no_fields_provided(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, _ = client
        resp = c.put(f"/customers/{uuid.uuid4()}", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /customers/<id>
# ---------------------------------------------------------------------------


class TestDeleteCustomer:
    def test_204_on_success(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.delete_customer.return_value = None

        resp = c.delete(f"/customers/{uuid.uuid4()}")

        assert resp.status_code == 204
        assert resp.data == b""

    def test_404_when_not_found(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.delete_customer.side_effect = CustomerNotFoundError("x")

        resp = c.delete(f"/customers/{uuid.uuid4()}")

        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "CUSTOMER_NOT_FOUND"
