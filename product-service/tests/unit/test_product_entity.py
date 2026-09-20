"""Unit tests for the Product domain entity."""

from __future__ import annotations

from decimal import Decimal

import pytest

from product_service.domain.entities.product import Product
from product_service.domain.exceptions import InvalidProductDataError


class TestProductCreate:
    def test_create_with_valid_data(self) -> None:
        product = Product.create(
            name="Notebook",
            price=Decimal("3500.00"),
            stock=10,
            description="Notebook para trabalho",
        )
        assert product.name == "Notebook"
        assert product.price == Decimal("3500.00")
        assert product.stock == 10
        assert product.description == "Notebook para trabalho"
        assert product.id is not None
        assert product.created_at is not None
        assert product.updated_at is not None
        assert product.created_at == product.updated_at

    def test_create_strips_whitespace_from_name_and_description(self) -> None:
        product = Product.create(
            name="  Notebook  ",
            price=3500.00,
            stock=10,
            description="  Notebook para trabalho  ",
        )
        assert product.name == "Notebook"
        assert product.description == "Notebook para trabalho"

    def test_create_with_no_description_defaults_to_empty_string(self) -> None:
        product = Product.create(name="Notebook", price=3500.00, stock=10)
        assert product.description == ""

    def test_create_raises_on_empty_name(self) -> None:
        with pytest.raises(InvalidProductDataError, match="name"):
            Product.create(name="", price=3500.00, stock=10)

    def test_create_raises_on_whitespace_only_name(self) -> None:
        with pytest.raises(InvalidProductDataError, match="name"):
            Product.create(name="   ", price=3500.00, stock=10)

    def test_create_raises_on_invalid_price_type(self) -> None:
        with pytest.raises(InvalidProductDataError, match="price must be a valid decimal number"):
            Product.create(name="Notebook", price="invalid", stock=10)

    def test_create_raises_on_price_less_than_or_equal_to_zero(self) -> None:
        with pytest.raises(InvalidProductDataError, match="price must be greater than zero"):
            Product.create(name="Notebook", price=0, stock=10)

        with pytest.raises(InvalidProductDataError, match="price must be greater than zero"):
            Product.create(name="Notebook", price=-10.00, stock=10)

    def test_create_raises_on_negative_stock(self) -> None:
        with pytest.raises(
            InvalidProductDataError, match="stock must be greater than or equal to zero"
        ):
            Product.create(name="Notebook", price=3500.00, stock=-1)

    def test_each_product_gets_unique_id(self) -> None:
        a = Product.create(name="A", price=10.00, stock=5)
        b = Product.create(name="B", price=20.00, stock=5)
        assert a.id != b.id


class TestProductUpdate:
    def _make_product(self) -> Product:
        return Product.create(name="Notebook", price=Decimal("3500.00"), stock=10)

    def test_update_name(self) -> None:
        product = self._make_product()
        original_updated_at = product.updated_at
        product.update(name="Notebook Updated")
        assert product.name == "Notebook Updated"
        assert product.updated_at >= original_updated_at

    def test_update_price(self) -> None:
        product = self._make_product()
        product.update(price=Decimal("4000.00"))
        assert product.price == Decimal("4000.00")

    def test_update_stock(self) -> None:
        product = self._make_product()
        product.update(stock=15)
        assert product.stock == 15

    def test_update_description(self) -> None:
        product = self._make_product()
        product.update(description="New description")
        assert product.description == "New description"

    def test_update_none_fields_are_ignored(self) -> None:
        product = self._make_product()
        original_name = product.name
        product.update(name=None, price=None, stock=None, description=None)
        assert product.name == original_name

    def test_update_strips_whitespace_from_name_and_description(self) -> None:
        product = self._make_product()
        product.update(name="  New Name  ", description="  New Desc  ")
        assert product.name == "New Name"
        assert product.description == "New Desc"

    def test_update_raises_on_empty_name(self) -> None:
        product = self._make_product()
        with pytest.raises(InvalidProductDataError, match="name"):
            product.update(name="")

    def test_update_raises_on_invalid_price_type(self) -> None:
        product = self._make_product()
        with pytest.raises(InvalidProductDataError, match="price must be a valid decimal number"):
            product.update(price="invalid")

    def test_update_raises_on_price_less_than_or_equal_to_zero(self) -> None:
        product = self._make_product()
        with pytest.raises(InvalidProductDataError, match="price must be greater than zero"):
            product.update(price=0)

        with pytest.raises(InvalidProductDataError, match="price must be greater than zero"):
            product.update(price=-5.00)

    def test_update_raises_on_negative_stock(self) -> None:
        product = self._make_product()
        with pytest.raises(
            InvalidProductDataError, match="stock must be greater than or equal to zero"
        ):
            product.update(stock=-1)
