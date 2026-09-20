from __future__ import annotations


class InvalidProductDataError(Exception):
    """Raised when product data fails domain validation."""


class ProductNotFoundError(Exception):
    """Raised when a product cannot be found by the given identifier."""
