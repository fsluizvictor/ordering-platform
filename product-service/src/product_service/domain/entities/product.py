from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from product_service.domain.exceptions import InvalidProductDataError


@dataclass
class Product:
    id: uuid.UUID
    name: str
    description: str
    price: Decimal
    stock: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        name: str,
        price: Decimal | float | str,
        stock: int,
        description: str = "",
    ) -> Product:
        """Factory method that validates invariants before constructing the entity."""
        if not name or not name.strip():
            raise InvalidProductDataError("name is required and must not be empty")

        try:
            dec_price = Decimal(str(price))
        except Exception as exc:
            raise InvalidProductDataError("price must be a valid decimal number") from exc

        if dec_price <= 0:
            raise InvalidProductDataError("price must be greater than zero")

        if stock < 0:
            raise InvalidProductDataError("stock must be greater than or equal to zero")

        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            name=name.strip(),
            description=description.strip(),
            price=dec_price,
            stock=stock,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        name: str | None = None,
        price: Decimal | float | str | None = None,
        stock: int | None = None,
        description: str | None = None,
    ) -> None:
        """Apply a partial update; only non-None fields are changed."""
        if name is not None:
            if not name.strip():
                raise InvalidProductDataError("name cannot be empty")
            self.name = name.strip()

        if price is not None:
            try:
                dec_price = Decimal(str(price))
            except Exception as exc:
                raise InvalidProductDataError("price must be a valid decimal number") from exc
            if dec_price <= 0:
                raise InvalidProductDataError("price must be greater than zero")
            self.price = dec_price

        if stock is not None:
            if stock < 0:
                raise InvalidProductDataError("stock must be greater than or equal to zero")
            self.stock = stock

        if description is not None:
            self.description = description.strip()

        self.updated_at = datetime.now(UTC)
