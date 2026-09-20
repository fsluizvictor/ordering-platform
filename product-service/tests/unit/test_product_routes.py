"""Unit tests for Product HTTP routes — ProductService is mocked."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

from product_service.adapters.inbound.http.app import create_app
from product_service.application.services.product_service import ProductService
from product_service.domain.entities.product import Product
from product_service.domain.exceptions import (
    InvalidProductDataError,
    ProductNotFoundError,
)


def _make_product(**overrides: object) -> Product:
    defaults: dict = {
        "id": uuid.uuid4(),
        "name": "Notebook",
        "description": "Notebook para trabalho",
        "price": Decimal("3500.00"),
        "stock": 10,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Product(**defaults)


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock(spec=ProductService)


@pytest.fixture
def client(mock_service: MagicMock) -> Generator[tuple[FlaskClient, MagicMock], None, None]:
    # Patch _get_service so routes receive the mock — no DB involved.
    with patch(
        "product_service.adapters.inbound.http.routes._get_service",
        return_value=mock_service,
    ):
        app = create_app(session_factory=MagicMock())
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c, mock_service


# ---------------------------------------------------------------------------
# POST /products
# ---------------------------------------------------------------------------


class TestPostProducts:
    def test_201_on_valid_request(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        product = _make_product()
        svc.create_product.return_value = product

        resp = c.post(
            "/products",
            json={
                "name": "Notebook",
                "price": 3500.00,
                "stock": 10,
                "description": "Notebook para trabalho",
            },
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Notebook"
        assert data["price"] == 3500.00
        assert data["stock"] == 10
        assert "id" in data
        assert "created_at" in data

    def test_422_when_name_is_missing(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, _ = client
        resp = c.post("/products", json={"price": 3500.00, "stock": 10})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_422_when_price_is_missing(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, _ = client
        resp = c.post("/products", json={"name": "Notebook", "stock": 10})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_422_when_stock_is_missing(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, _ = client
        resp = c.post("/products", json={"name": "Notebook", "price": 3500.00})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_422_when_stock_is_not_an_integer(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, _ = client
        resp = c.post("/products", json={"name": "Notebook", "price": 3500.00, "stock": "ten"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

        resp2 = c.post("/products", json={"name": "Notebook", "price": 3500.00, "stock": True})
        assert resp2.status_code == 422
        assert resp2.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_422_when_domain_rejects_data(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.create_product.side_effect = InvalidProductDataError("price must be greater than zero")

        resp = c.post("/products", json={"name": "Notebook", "price": -10.00, "stock": 10})

        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# GET /products
# ---------------------------------------------------------------------------


class TestGetProducts:
    def test_200_returns_list(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.list_products.return_value = [_make_product(), _make_product()]

        resp = c.get("/products")

        assert resp.status_code == 200
        assert len(resp.get_json()) == 2

    def test_200_returns_empty_list(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.list_products.return_value = []

        resp = c.get("/products")

        assert resp.status_code == 200
        assert resp.get_json() == []


# ---------------------------------------------------------------------------
# GET /products/count
# ---------------------------------------------------------------------------


class TestGetProductsCount:
    def test_200_returns_count(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.count_products.return_value = 7

        resp = c.get("/products/count")

        assert resp.status_code == 200
        assert resp.get_json() == {"count": 7}


# ---------------------------------------------------------------------------
# GET /products/name/<name>
# ---------------------------------------------------------------------------


class TestGetProductsByName:
    def test_200_returns_matching_products(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.find_by_name.return_value = [_make_product(name="Notebook")]

        resp = c.get("/products/name/Notebook")

        assert resp.status_code == 200
        assert resp.get_json()[0]["name"] == "Notebook"
        svc.find_by_name.assert_called_once_with("Notebook")


# ---------------------------------------------------------------------------
# GET /products/<id>
# ---------------------------------------------------------------------------


class TestGetProductById:
    def test_200_when_found(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        product = _make_product()
        svc.get_product.return_value = product

        resp = c.get(f"/products/{product.id}")

        assert resp.status_code == 200
        assert resp.get_json()["id"] == str(product.id)

    def test_404_when_not_found(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.get_product.side_effect = ProductNotFoundError("x")

        resp = c.get(f"/products/{uuid.uuid4()}")

        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "PRODUCT_NOT_FOUND"


# ---------------------------------------------------------------------------
# PUT /products/<id>
# ---------------------------------------------------------------------------


class TestPutProduct:
    def test_200_on_valid_update(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        product = _make_product(name="Updated")
        svc.update_product.return_value = product

        resp = c.put(f"/products/{product.id}", json={"name": "Updated"})

        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Updated"

    def test_404_when_not_found(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.update_product.side_effect = ProductNotFoundError("x")

        resp = c.put(f"/products/{uuid.uuid4()}", json={"name": "New"})

        assert resp.status_code == 404

    def test_422_on_no_fields_provided(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, _ = client
        resp = c.put(f"/products/{uuid.uuid4()}", json={})
        assert resp.status_code == 422

    def test_422_on_invalid_stock_type(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, _ = client
        resp = c.put(f"/products/{uuid.uuid4()}", json={"stock": "ten"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /products/<id>
# ---------------------------------------------------------------------------


class TestDeleteProduct:
    def test_204_on_success(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.delete_product.return_value = None

        resp = c.delete(f"/products/{uuid.uuid4()}")

        assert resp.status_code == 204
        assert resp.data == b""

    def test_404_when_not_found(self, client: tuple[FlaskClient, MagicMock]) -> None:
        c, svc = client
        svc.delete_product.side_effect = ProductNotFoundError("x")

        resp = c.delete(f"/products/{uuid.uuid4()}")

        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "PRODUCT_NOT_FOUND"
