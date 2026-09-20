from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from product_service.domain.entities.product import Product


class ProductRepository(ABC):
    @abstractmethod
    def save(self, product: Product) -> Product: ...

    @abstractmethod
    def find_by_id(self, product_id: uuid.UUID) -> Product | None: ...

    @abstractmethod
    def find_by_name(self, name: str) -> list[Product]: ...

    @abstractmethod
    def find_all(self) -> list[Product]: ...

    @abstractmethod
    def update(self, product: Product) -> Product: ...

    @abstractmethod
    def delete(self, product_id: uuid.UUID) -> None: ...

    @abstractmethod
    def count(self) -> int: ...
