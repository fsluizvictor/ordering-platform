from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from customer_service.domain.entities.customer import Customer


class CustomerRepository(ABC):
    @abstractmethod
    def save(self, customer: Customer) -> Customer: ...

    @abstractmethod
    def find_by_id(self, customer_id: uuid.UUID) -> Customer | None: ...

    @abstractmethod
    def find_by_email(self, email: str) -> Customer | None: ...

    @abstractmethod
    def find_by_name(self, name: str) -> list[Customer]: ...

    @abstractmethod
    def find_all(self) -> list[Customer]: ...

    @abstractmethod
    def update(self, customer: Customer) -> Customer: ...

    @abstractmethod
    def delete(self, customer_id: uuid.UUID) -> None: ...

    @abstractmethod
    def count(self) -> int: ...
