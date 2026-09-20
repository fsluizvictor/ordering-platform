from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from customer_service.domain.exceptions import InvalidCustomerDataError


@dataclass
class Customer:
    id: uuid.UUID
    name: str
    email: str
    phone: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, name: str, email: str, phone: str = "") -> Customer:
        """Factory method that validates invariants before constructing the entity."""
        if not name or not name.strip():
            raise InvalidCustomerDataError("name is required and must not be empty")
        if not email or not email.strip():
            raise InvalidCustomerDataError("email is required")
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            name=name.strip(),
            email=email.strip(),
            phone=phone,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> None:
        """Apply a partial update; only non-None fields are changed."""
        if name is not None:
            if not name.strip():
                raise InvalidCustomerDataError("name cannot be empty")
            self.name = name.strip()
        if email is not None:
            if not email.strip():
                raise InvalidCustomerDataError("email cannot be empty")
            self.email = email.strip()
        if phone is not None:
            self.phone = phone
        self.updated_at = datetime.now(UTC)
