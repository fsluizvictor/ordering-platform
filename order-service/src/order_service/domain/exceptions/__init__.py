from __future__ import annotations


class InvalidOrderError(Exception):
    """Raised when an order fails domain validation."""


class OrderNotFoundError(Exception):
    """Raised when an order cannot be found by the given identifier."""


class OrderStatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""


class OrderNotEditableError(Exception):
    """Raised when an operation requires a PENDING status but the order is not PENDING."""


class OrderNotDeletableError(Exception):
    """Raised when deletion is attempted on an order in a non-deletable status."""
