"""Unit tests for CustomerService — repository is mocked."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

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
def repo() -> MagicMock:
    mock = MagicMock()
    mock.find_by_email.return_value = None  # email is available by default
    return mock


@pytest.fixture
def service(repo: MagicMock) -> CustomerService:
    return CustomerService(repo)


class TestCreateCustomer:
    def test_creates_and_persists_customer(self, service: CustomerService, repo: MagicMock) -> None:
        customer = _make_customer()
        repo.save.return_value = customer

        result = service.create_customer(name="Alice", email="alice@example.com")

        repo.find_by_email.assert_called_once_with("alice@example.com")
        repo.save.assert_called_once()
        assert result is customer

    def test_raises_when_email_already_exists(
        self, service: CustomerService, repo: MagicMock
    ) -> None:
        repo.find_by_email.return_value = _make_customer()

        with pytest.raises(CustomerEmailAlreadyExistsError):
            service.create_customer(name="Bob", email="alice@example.com")

        repo.save.assert_not_called()

    def test_raises_on_empty_name_via_entity_validation(
        self, service: CustomerService, repo: MagicMock
    ) -> None:
        with pytest.raises(InvalidCustomerDataError):
            service.create_customer(name="", email="alice@example.com")


class TestGetCustomer:
    def test_returns_customer_when_found(self, service: CustomerService, repo: MagicMock) -> None:
        customer = _make_customer()
        repo.find_by_id.return_value = customer

        result = service.get_customer(customer.id)

        assert result is customer

    def test_raises_when_not_found(self, service: CustomerService, repo: MagicMock) -> None:
        repo.find_by_id.return_value = None

        with pytest.raises(CustomerNotFoundError):
            service.get_customer(uuid.uuid4())


class TestFindByName:
    def test_returns_matching_customers(self, service: CustomerService, repo: MagicMock) -> None:
        customers = [_make_customer(name="Alice"), _make_customer(name="Alice Wonder")]
        repo.find_by_name.return_value = customers

        result = service.find_by_name("Alice")

        repo.find_by_name.assert_called_once_with("Alice")
        assert result == customers


class TestListCustomers:
    def test_returns_all_customers(self, service: CustomerService, repo: MagicMock) -> None:
        customers = [_make_customer(), _make_customer()]
        repo.find_all.return_value = customers

        result = service.list_customers()

        assert result == customers


class TestUpdateCustomer:
    def test_updates_customer_successfully(self, service: CustomerService, repo: MagicMock) -> None:
        customer = _make_customer()
        repo.find_by_id.return_value = customer
        repo.update.return_value = customer

        result = service.update_customer(customer.id, name="Alice Updated")

        repo.update.assert_called_once_with(customer)
        assert result is customer

    def test_raises_when_not_found(self, service: CustomerService, repo: MagicMock) -> None:
        repo.find_by_id.return_value = None

        with pytest.raises(CustomerNotFoundError):
            service.update_customer(uuid.uuid4(), name="New")

    def test_raises_when_new_email_is_taken(
        self, service: CustomerService, repo: MagicMock
    ) -> None:
        existing = _make_customer(email="alice@example.com")
        other = _make_customer(email="other@example.com")
        repo.find_by_id.return_value = existing
        # Simulate another customer owning the target email.
        repo.find_by_email.return_value = other

        with pytest.raises(CustomerEmailAlreadyExistsError):
            service.update_customer(existing.id, email="other@example.com")

        repo.update.assert_not_called()

    def test_no_email_conflict_check_when_email_unchanged(
        self, service: CustomerService, repo: MagicMock
    ) -> None:
        customer = _make_customer(email="alice@example.com")
        repo.find_by_id.return_value = customer
        repo.update.return_value = customer

        service.update_customer(customer.id, email="alice@example.com")

        # Email is the same as current — uniqueness check should not be triggered.
        repo.find_by_email.assert_not_called()


class TestDeleteCustomer:
    def test_deletes_existing_customer(self, service: CustomerService, repo: MagicMock) -> None:
        customer = _make_customer()
        repo.find_by_id.return_value = customer

        service.delete_customer(customer.id)

        repo.delete.assert_called_once_with(customer.id)

    def test_raises_when_not_found(self, service: CustomerService, repo: MagicMock) -> None:
        repo.find_by_id.return_value = None

        with pytest.raises(CustomerNotFoundError):
            service.delete_customer(uuid.uuid4())

        repo.delete.assert_not_called()


class TestCountCustomers:
    def test_returns_count(self, service: CustomerService, repo: MagicMock) -> None:
        repo.count.return_value = 42

        assert service.count_customers() == 42
