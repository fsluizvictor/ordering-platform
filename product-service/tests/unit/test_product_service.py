"""Unit tests for ProductService — repository is mocked."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

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
def repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(repo: MagicMock) -> ProductService:
    return ProductService(repo)


class TestCreateProduct:
    def test_creates_and_persists_product(self, service: ProductService, repo: MagicMock) -> None:
        product = _make_product()
        repo.save.return_value = product

        result = service.create_product(
            name="Notebook",
            price=Decimal("3500.00"),
            stock=10,
            description="Notebook para trabalho",
        )

        repo.save.assert_called_once()
        assert result is product

    def test_raises_on_empty_name_via_entity_validation(
        self, service: ProductService, repo: MagicMock
    ) -> None:
        with pytest.raises(InvalidProductDataError):
            service.create_product(name="", price=3500.00, stock=10)


class TestGetProduct:
    def test_returns_product_when_found(self, service: ProductService, repo: MagicMock) -> None:
        product = _make_product()
        repo.find_by_id.return_value = product

        result = service.get_product(product.id)

        assert result is product

    def test_raises_when_not_found(self, service: ProductService, repo: MagicMock) -> None:
        repo.find_by_id.return_value = None

        with pytest.raises(ProductNotFoundError):
            service.get_product(uuid.uuid4())


class TestFindByName:
    def test_returns_matching_products(self, service: ProductService, repo: MagicMock) -> None:
        products = [_make_product(name="Notebook"), _make_product(name="Notebook Pro")]
        repo.find_by_name.return_value = products

        result = service.find_by_name("Notebook")

        repo.find_by_name.assert_called_once_with("Notebook")
        assert result == products


class TestListProducts:
    def test_returns_all_products(self, service: ProductService, repo: MagicMock) -> None:
        products = [_make_product(), _make_product()]
        repo.find_all.return_value = products

        result = service.list_products()

        assert result == products


class TestUpdateProduct:
    def test_updates_product_successfully(self, service: ProductService, repo: MagicMock) -> None:
        product = _make_product()
        repo.find_by_id.return_value = product
        repo.update.return_value = product

        result = service.update_product(product.id, name="Notebook Updated")

        repo.update.assert_called_once_with(product)
        assert result is product

    def test_raises_when_not_found(self, service: ProductService, repo: MagicMock) -> None:
        repo.find_by_id.return_value = None

        with pytest.raises(ProductNotFoundError):
            service.update_product(uuid.uuid4(), name="New")


class TestDeleteProduct:
    def test_deletes_existing_product(self, service: ProductService, repo: MagicMock) -> None:
        product = _make_product()
        repo.find_by_id.return_value = product

        service.delete_product(product.id)

        repo.delete.assert_called_once_with(product.id)

    def test_raises_when_not_found(self, service: ProductService, repo: MagicMock) -> None:
        repo.find_by_id.return_value = None

        with pytest.raises(ProductNotFoundError):
            service.delete_product(uuid.uuid4())

        repo.delete.assert_not_called()


class TestCountProducts:
    def test_returns_count(self, service: ProductService, repo: MagicMock) -> None:
        repo.count.return_value = 42

        assert service.count_products() == 42
