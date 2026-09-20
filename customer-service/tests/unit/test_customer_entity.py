"""Unit tests for the Customer domain entity."""

from __future__ import annotations

import pytest

from customer_service.domain.entities.customer import Customer
from customer_service.domain.exceptions import InvalidCustomerDataError


class TestCustomerCreate:
    def test_create_with_valid_data(self) -> None:
        customer = Customer.create(name="Alice", email="alice@example.com", phone="11999999999")
        assert customer.name == "Alice"
        assert customer.email == "alice@example.com"
        assert customer.phone == "11999999999"
        assert customer.id is not None
        assert customer.created_at is not None
        assert customer.updated_at is not None
        assert customer.created_at == customer.updated_at

    def test_create_strips_whitespace_from_name_and_email(self) -> None:
        customer = Customer.create(name="  Bob  ", email="  bob@example.com  ")
        assert customer.name == "Bob"
        assert customer.email == "bob@example.com"

    def test_create_with_no_phone_defaults_to_empty_string(self) -> None:
        customer = Customer.create(name="Carol", email="carol@example.com")
        assert customer.phone == ""

    def test_create_raises_on_empty_name(self) -> None:
        with pytest.raises(InvalidCustomerDataError, match="name"):
            Customer.create(name="", email="x@example.com")

    def test_create_raises_on_whitespace_only_name(self) -> None:
        with pytest.raises(InvalidCustomerDataError, match="name"):
            Customer.create(name="   ", email="x@example.com")

    def test_create_raises_on_empty_email(self) -> None:
        with pytest.raises(InvalidCustomerDataError, match="email"):
            Customer.create(name="Alice", email="")

    def test_create_raises_on_whitespace_only_email(self) -> None:
        with pytest.raises(InvalidCustomerDataError, match="email"):
            Customer.create(name="Alice", email="   ")

    def test_each_customer_gets_unique_id(self) -> None:
        a = Customer.create(name="A", email="a@example.com")
        b = Customer.create(name="B", email="b@example.com")
        assert a.id != b.id


class TestCustomerUpdate:
    def _make_customer(self) -> Customer:
        return Customer.create(name="Alice", email="alice@example.com", phone="123")

    def test_update_name(self) -> None:
        customer = self._make_customer()
        original_updated_at = customer.updated_at
        customer.update(name="Alice Updated")
        assert customer.name == "Alice Updated"
        assert customer.updated_at >= original_updated_at

    def test_update_email(self) -> None:
        customer = self._make_customer()
        customer.update(email="new@example.com")
        assert customer.email == "new@example.com"

    def test_update_phone(self) -> None:
        customer = self._make_customer()
        customer.update(phone="999")
        assert customer.phone == "999"

    def test_update_none_fields_are_ignored(self) -> None:
        customer = self._make_customer()
        original_name = customer.name
        customer.update(name=None, email=None, phone=None)
        assert customer.name == original_name

    def test_update_strips_whitespace_from_name(self) -> None:
        customer = self._make_customer()
        customer.update(name="  New Name  ")
        assert customer.name == "New Name"

    def test_update_raises_on_empty_name(self) -> None:
        customer = self._make_customer()
        with pytest.raises(InvalidCustomerDataError, match="name"):
            customer.update(name="")

    def test_update_raises_on_empty_email(self) -> None:
        customer = self._make_customer()
        with pytest.raises(InvalidCustomerDataError, match="email"):
            customer.update(email="")
