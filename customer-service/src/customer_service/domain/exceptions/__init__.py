from __future__ import annotations


class InvalidCustomerDataError(Exception):
    """Raised when customer data fails domain validation."""


class CustomerNotFoundError(Exception):
    """Raised when a customer cannot be found by the given identifier."""


class CustomerEmailAlreadyExistsError(Exception):
    """Raised when a customer email is already registered."""
