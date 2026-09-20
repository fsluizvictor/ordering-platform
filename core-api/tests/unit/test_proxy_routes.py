"""Unit tests for Core API proxy routes.

The proxy uses urllib.request.urlopen internally.
We patch it so tests run without real network calls.
"""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core_api.adapters.inbound.http.app import create_app


@pytest.fixture()
def app():
    """Return a test Flask application with settings mocked."""
    with (
        patch.dict(
            "os.environ",
            {
                "CUSTOMER_SERVICE_URL": "http://customer-service:8001",
                "PRODUCT_SERVICE_URL": "http://product-service:8002",
                "ORDER_SERVICE_URL": "http://order-service:8003",
                "PROXY_TIMEOUT": "5",
            },
        ),
    ):
        flask_app = create_app()
        flask_app.config["TESTING"] = True
        yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


# ── Helpers ───────────────────────────────────────────────────────────────


def _mock_response(
    body: Any, status: int = 200, content_type: str = "application/json"
) -> MagicMock:
    """Build a fake urllib response with .read(), .status, and .headers."""
    raw = json.dumps(body).encode() if not isinstance(body, bytes) else body
    mock = MagicMock()
    mock.read.return_value = raw
    mock.status = status
    mock.headers = {"Content-Type": content_type}
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


_URLOPEN = "core_api.adapters.inbound.http.proxy.urllib.request.urlopen"


# ── Health ────────────────────────────────────────────────────────────────


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


# ── Correlation ID ────────────────────────────────────────────────────────


def test_correlation_id_is_generated_when_absent(client):
    with patch(_URLOPEN, return_value=_mock_response([])):
        resp = client.get("/api/v1/customers")
    assert "X-Correlation-ID" in resp.headers
    assert resp.headers["X-Correlation-ID"] != ""


def test_correlation_id_is_forwarded_when_present(client):
    correlation_id = "test-correlation-123"
    with patch(_URLOPEN, return_value=_mock_response([])) as mock_open:
        resp = client.get("/api/v1/customers", headers={"X-Correlation-ID": correlation_id})

    # The response should echo back the same correlation ID.
    assert resp.headers.get("X-Correlation-ID") == correlation_id

    # The upstream request must have received the correlation ID.
    req_sent = mock_open.call_args[0][0]
    assert req_sent.get_header("X-correlation-id") == correlation_id


# ── Customer routing ──────────────────────────────────────────────────────


def test_customers_list_routed_to_customer_service(client):
    payload = [{"id": "abc", "name": "Alice"}]
    with patch(_URLOPEN, return_value=_mock_response(payload)) as mock_open:
        resp = client.get("/api/v1/customers")

    assert resp.status_code == 200
    called_url: str = mock_open.call_args[0][0].full_url
    assert "customer-service:8001" in called_url
    assert "/customers" in called_url


def test_customers_post_routed_to_customer_service(client):
    created = {"id": "1", "name": "Bob", "email": "bob@example.com"}
    with patch(_URLOPEN, return_value=_mock_response(created, 201)) as mock_open:
        resp = client.post(
            "/api/v1/customers",
            json={"name": "Bob", "email": "bob@example.com"},
        )

    assert resp.status_code == 201
    called_url: str = mock_open.call_args[0][0].full_url
    assert "customer-service:8001" in called_url


# ── Product routing ───────────────────────────────────────────────────────


def test_products_list_routed_to_product_service(client):
    payload = [{"id": "p1", "name": "Widget"}]
    with patch(_URLOPEN, return_value=_mock_response(payload)) as mock_open:
        resp = client.get("/api/v1/products")

    assert resp.status_code == 200
    called_url: str = mock_open.call_args[0][0].full_url
    assert "product-service:8002" in called_url
    assert "/products" in called_url


# ── Error translation ─────────────────────────────────────────────────────


def test_4xx_from_upstream_forwarded_to_client(client):
    import urllib.error

    error_payload = json.dumps(
        {"error": {"code": "CUSTOMER_NOT_FOUND", "message": "not found", "request_id": None}}
    ).encode()
    http_error = urllib.error.HTTPError(
        url="http://customer-service:8001/customers/bad-id",
        code=404,
        msg="Not Found",
        hdrs=MagicMock(get=lambda k, d=None: "application/json"),
        fp=BytesIO(error_payload),
    )
    http_error.read = lambda: error_payload

    with patch(_URLOPEN, side_effect=http_error):
        resp = client.get("/api/v1/customers/00000000-0000-0000-0000-000000000001")

    assert resp.status_code == 404


def test_5xx_from_upstream_returns_internal_error(client):
    import urllib.error

    http_error = urllib.error.HTTPError(
        url="http://customer-service:8001/customers",
        code=500,
        msg="Internal Server Error",
        hdrs=MagicMock(get=lambda k, d=None: "application/json"),
        fp=BytesIO(b"{}"),
    )
    http_error.read = lambda: b"{}"

    with patch(_URLOPEN, side_effect=http_error):
        resp = client.get("/api/v1/customers")

    assert resp.status_code == 500
    data = resp.get_json()
    assert data["error"]["code"] == "INTERNAL_ERROR"


def test_connection_error_returns_internal_error(client):
    with patch(_URLOPEN, side_effect=ConnectionError("refused")):
        resp = client.get("/api/v1/customers")

    assert resp.status_code == 500
    data = resp.get_json()
    assert data["error"]["code"] == "INTERNAL_ERROR"


# ── Swagger / OpenAPI ─────────────────────────────────────────────────────


def test_swagger_ui_returns_html(client):
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert b"swagger" in resp.data.lower()


def test_openapi_yaml_is_served(client):
    resp = client.get("/openapi.yaml")
    assert resp.status_code == 200
    # Must be YAML content containing expected OpenAPI marker.
    assert b"openapi" in resp.data
