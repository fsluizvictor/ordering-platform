from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from order_service.domain.entities.order import Order


class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order) -> Order: ...

    @abstractmethod
    def find_by_external_id(self, external_id: uuid.UUID) -> Order | None: ...

    @abstractmethod
    def find_all(self) -> list[Order]: ...

    @abstractmethod
    def update(self, order: Order) -> Order: ...

    @abstractmethod
    def delete(self, order_id: uuid.UUID) -> None: ...

    @abstractmethod
    def count(self) -> int: ...
