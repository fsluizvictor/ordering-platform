from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerData:
    id: uuid.UUID
    name: str
    email: str


class CustomerLookupPort(ABC):
    @abstractmethod
    def get_customer(self, customer_id: uuid.UUID) -> CustomerData | None: ...
