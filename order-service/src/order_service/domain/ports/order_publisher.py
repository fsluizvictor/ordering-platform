from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OrderItemPayload:
    product_id: uuid.UUID
    quantity: int


@dataclass(frozen=True)
class OrderCreatedEvent:
    event_id: uuid.UUID
    event_type: str
    occurred_at: datetime
    correlation_id: uuid.UUID | None
    external_id: uuid.UUID
    customer_id: uuid.UUID
    items: list[OrderItemPayload]


class OrderPublisher(ABC):
    @abstractmethod
    def publish_order_created(self, event: OrderCreatedEvent) -> None: ...
