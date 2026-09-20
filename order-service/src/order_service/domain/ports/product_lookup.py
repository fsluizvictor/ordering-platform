from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProductData:
    id: uuid.UUID
    name: str
    price: Decimal
    stock: int


class ProductLookupPort(ABC):
    @abstractmethod
    def get_product(self, product_id: uuid.UUID) -> ProductData | None: ...
