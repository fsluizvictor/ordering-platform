from __future__ import annotations

import logging
import uuid

from customer_service.domain.entities.customer import Customer
from customer_service.domain.exceptions import (
    CustomerEmailAlreadyExistsError,
    CustomerNotFoundError,
)
from customer_service.domain.ports.customer_repository import CustomerRepository

logger = logging.getLogger(__name__)


class CustomerService:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repo = repository

    def create_customer(self, name: str, email: str, phone: str = "") -> Customer:
        # Application-level check so we can raise a clean domain error before hitting the DB.
        # The repository also guards against duplicates via the UNIQUE constraint.
        normalized_email = email.strip() if email else email
        if self._repo.find_by_email(normalized_email) is not None:
            raise CustomerEmailAlreadyExistsError(f"Email already in use: {email}")
        customer = Customer.create(name=name, email=email, phone=phone)
        saved = self._repo.save(customer)
        logger.info("Customer created: %s", saved.id)
        return saved

    def get_customer(self, customer_id: uuid.UUID) -> Customer:
        customer = self._repo.find_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError(str(customer_id))
        return customer

    def find_by_name(self, name: str) -> list[Customer]:
        return self._repo.find_by_name(name)

    def list_customers(self) -> list[Customer]:
        return self._repo.find_all()

    def update_customer(
        self,
        customer_id: uuid.UUID,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> Customer:
        customer = self._repo.find_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError(str(customer_id))
        # Check uniqueness only when the email is actually changing.
        if email is not None and email.strip() != customer.email:
            if self._repo.find_by_email(email.strip()) is not None:
                raise CustomerEmailAlreadyExistsError(f"Email already in use: {email}")
        customer.update(name=name, email=email, phone=phone)
        updated = self._repo.update(customer)
        logger.info("Customer updated: %s", customer_id)
        return updated

    def delete_customer(self, customer_id: uuid.UUID) -> None:
        customer = self._repo.find_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError(str(customer_id))
        self._repo.delete(customer_id)
        logger.info("Customer deleted: %s", customer_id)

    def count_customers(self) -> int:
        return self._repo.count()
