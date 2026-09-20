from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from customer_service.adapters.outbound.persistence.models import CustomerModel
from customer_service.domain.entities.customer import Customer
from customer_service.domain.exceptions import CustomerEmailAlreadyExistsError
from customer_service.domain.ports.customer_repository import CustomerRepository


class SQLAlchemyCustomerRepository(CustomerRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, customer: Customer) -> Customer:
        model = _to_model(customer)
        self._session.add(model)
        try:
            # Flush immediately so IntegrityError is raised here, not at commit,
            # allowing the route to return the correct HTTP error code.
            self._session.flush()
        except IntegrityError:
            self._session.rollback()
            # Translate the infrastructure error into a domain exception so the
            # SQLAlchemy IntegrityError never leaks beyond this adapter boundary.
            raise CustomerEmailAlreadyExistsError(
                f"Email already exists: {customer.email}"
            ) from None
        return customer

    def find_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        model = self._session.get(CustomerModel, customer_id)
        return _to_entity(model) if model else None

    def find_by_email(self, email: str) -> Customer | None:
        stmt = select(CustomerModel).where(CustomerModel.email == email)
        model = self._session.scalar(stmt)
        return _to_entity(model) if model else None

    def find_by_name(self, name: str) -> list[Customer]:
        # Case-insensitive partial match so callers can search by partial name.
        stmt = select(CustomerModel).where(CustomerModel.name.ilike(f"%{name}%"))
        return [_to_entity(m) for m in self._session.scalars(stmt).all()]

    def find_all(self) -> list[Customer]:
        stmt = select(CustomerModel)
        return [_to_entity(m) for m in self._session.scalars(stmt).all()]

    def update(self, customer: Customer) -> Customer:
        model = self._session.get(CustomerModel, customer.id)
        if model is None:
            # Should not happen: service validated existence before calling update.
            raise ValueError(f"Customer not found in persistence: {customer.id}")
        model.name = customer.name
        model.email = customer.email
        model.phone = customer.phone
        model.updated_at = customer.updated_at
        try:
            self._session.flush()
        except IntegrityError:
            self._session.rollback()
            raise CustomerEmailAlreadyExistsError(
                f"Email already exists: {customer.email}"
            ) from None
        return customer

    def delete(self, customer_id: uuid.UUID) -> None:
        model = self._session.get(CustomerModel, customer_id)
        if model is not None:
            self._session.delete(model)
            self._session.flush()

    def count(self) -> int:
        stmt = select(func.count()).select_from(CustomerModel)
        return self._session.scalar(stmt) or 0


# Module-level helpers keep the class free of static methods and stay DRY.


def _to_model(customer: Customer) -> CustomerModel:
    return CustomerModel(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


def _to_entity(model: CustomerModel) -> Customer:
    return Customer(
        id=model.id,
        name=model.name,
        email=model.email,
        phone=model.phone,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
