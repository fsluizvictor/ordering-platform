"""
End-to-end tests for the complete Order flow.

Requires the full Docker Compose environment to be running:
    docker compose up --build

Base URL: http://localhost:8000/api/v1
"""

from __future__ import annotations

import time
import uuid

import pytest
import requests

BASE_URL = "http://localhost:8000/api/v1"
POLL_TIMEOUT = 10  # seconds
POLL_INTERVAL = 0.5  # seconds


# ── Helpers ───────────────────────────────────────────────────────────────


def _poll_order_status(
    external_id: str,
    expected_status: str,
    timeout: float = POLL_TIMEOUT,
) -> dict:
    """Poll GET /orders/{external_id} until status matches or timeout is reached."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = requests.get(f"{BASE_URL}/orders/{external_id}", timeout=5)
        assert resp.status_code == 200, (
            f"Unexpected status while polling order: {resp.status_code} {resp.text}"
        )
        order = resp.json()
        if order["status"] == expected_status:
            return order
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(
        f"Order {external_id} did not reach status '{expected_status}' within {timeout}s. "
        f"Last status: {order['status']}"
    )


def _create_customer(name: str | None = None) -> dict:
    """Create a Customer and return its JSON body."""
    unique = uuid.uuid4().hex[:8]
    payload = {
        "name": name or f"Test Customer {unique}",
        "email": f"customer-{unique}@test.com",
        "phone": f"+1555{unique[:7]}",
    }
    resp = requests.post(f"{BASE_URL}/customers", json=payload, timeout=5)
    assert resp.status_code == 201, f"Failed to create customer: {resp.status_code} {resp.text}"
    return resp.json()


def _create_product(price: str = "50.00", stock: int = 10) -> dict:
    """Create a Product and return its JSON body."""
    unique = uuid.uuid4().hex[:8]
    payload = {
        "name": f"Test Product {unique}",
        "description": "E2E test product",
        "price": price,
        "stock": stock,
    }
    resp = requests.post(f"{BASE_URL}/products", json=payload, timeout=5)
    assert resp.status_code == 201, f"Failed to create product: {resp.status_code} {resp.text}"
    return resp.json()


def _create_order(customer_id: str, items: list[dict], idempotency_key: str | None = None) -> dict:
    """POST /orders and return the 202 response body."""
    headers = {}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    payload = {"customer_id": customer_id, "items": items}
    resp = requests.post(f"{BASE_URL}/orders", json=payload, headers=headers, timeout=5)
    assert resp.status_code == 202, (
        f"Expected 202 from POST /orders, got {resp.status_code}: {resp.text}"
    )
    return resp.json()


# ── Scenarios ─────────────────────────────────────────────────────────────


@pytest.mark.e2e
class TestE2E:
    """End-to-end tests against the live Docker Compose environment."""

    def test_happy_path_order_completed_with_correct_total(self) -> None:
        """
        Scenario 1 — Happy Path.

        1. Create Customer.
        2. Create Product (stock ≥ quantity).
        3. Create Order referencing both.
        4. Poll until COMPLETED.
        5. Assert total_amount == quantity × product.price.
        6. Assert OrderItem.unit_price == product.price.
        """
        customer = _create_customer()
        product = _create_product(price="25.00", stock=10)

        quantity = 3
        order_resp = _create_order(
            customer_id=customer["id"],
            items=[{"product_id": product["id"], "quantity": quantity}],
        )

        external_id = order_resp["external_id"]
        assert order_resp["status"] == "PENDING"

        order = _poll_order_status(external_id, "COMPLETED")

        expected_total = quantity * float(product["price"])
        assert float(order["total_amount"]) == pytest.approx(expected_total), (
            f"total_amount mismatch: expected {expected_total}, got {order['total_amount']}"
        )

        items = order.get("items", [])
        assert len(items) == 1, f"Expected 1 order item, got {len(items)}"
        assert float(items[0]["unit_price"]) == pytest.approx(float(product["price"])), (
            f"unit_price mismatch: expected {product['price']}, got {items[0]['unit_price']}"
        )

    def test_nonexistent_customer_order_fails(self) -> None:
        """
        Scenario 2 — Non-existent Customer.

        POST /orders with an unknown customer_id → 202 (accepted).
        Poll until status == FAILED.
        """
        unknown_customer_id = str(uuid.uuid4())

        # Need at least one valid-looking item; product existence is checked after customer
        order_resp = _create_order(
            customer_id=unknown_customer_id,
            items=[{"product_id": str(uuid.uuid4()), "quantity": 1}],
        )

        external_id = order_resp["external_id"]
        _poll_order_status(external_id, "FAILED")

    def test_nonexistent_product_order_fails(self) -> None:
        """
        Scenario 3 — Non-existent Product.

        1. Create a real Customer.
        2. POST /orders with an unknown product_id → 202.
        3. Poll until FAILED.
        """
        customer = _create_customer()
        unknown_product_id = str(uuid.uuid4())

        order_resp = _create_order(
            customer_id=customer["id"],
            items=[{"product_id": unknown_product_id, "quantity": 1}],
        )

        external_id = order_resp["external_id"]
        _poll_order_status(external_id, "FAILED")

    def test_insufficient_stock_order_fails(self) -> None:
        """
        Scenario 4 — Insufficient Stock.

        1. Create Customer.
        2. Create Product with stock=1.
        3. POST /orders requesting quantity=5.
        4. Poll until FAILED.
        """
        customer = _create_customer()
        product = _create_product(price="10.00", stock=1)

        order_resp = _create_order(
            customer_id=customer["id"],
            items=[{"product_id": product["id"], "quantity": 5}],
        )

        external_id = order_resp["external_id"]
        _poll_order_status(external_id, "FAILED")
