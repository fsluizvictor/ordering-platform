from __future__ import annotations

import os

from flask import Blueprint, Response, send_file

from core_api.adapters.inbound.http.proxy import forward
from core_api.config.settings import (
    customer_service_url,
    order_service_url,
    product_service_url,
    proxy_timeout,
)

api_bp = Blueprint("api", __name__)

_OPENAPI_PATH = os.path.join(os.path.dirname(__file__), "openapi.yaml")

_SWAGGER_UI_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Ordering Platform — API Docs</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet"
        href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  SwaggerUIBundle({
    url: "/openapi.yaml",
    dom_id: "#swagger-ui",
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
    layout: "BaseLayout",
  });
</script>
</body>
</html>
"""


# ── Docs ──────────────────────────────────────────────────────────────────


@api_bp.get("/docs")
def swagger_ui() -> tuple[str, int, dict[str, str]]:
    return _SWAGGER_UI_HTML, 200, {"Content-Type": "text/html"}


@api_bp.get("/openapi.yaml")
def openapi_yaml() -> Response:
    return send_file(_OPENAPI_PATH, mimetype="application/yaml")


# ── Customers ─────────────────────────────────────────────────────────────


@api_bp.route("/api/v1/customers", methods=["GET", "POST"])
def customers() -> tuple[Response, int]:
    return forward(f"{customer_service_url()}/customers", proxy_timeout())


@api_bp.route("/api/v1/customers/count", methods=["GET"])
def customers_count() -> tuple[Response, int]:
    return forward(f"{customer_service_url()}/customers/count", proxy_timeout())


@api_bp.route("/api/v1/customers/name/<path:name>", methods=["GET"])
def customers_by_name(name: str) -> tuple[Response, int]:
    return forward(f"{customer_service_url()}/customers/name/{name}", proxy_timeout())


@api_bp.route("/api/v1/customers/<uuid:customer_id>", methods=["GET", "PUT", "DELETE"])
def customer_by_id(customer_id: str) -> tuple[Response, int]:
    return forward(f"{customer_service_url()}/customers/{customer_id}", proxy_timeout())


# ── Products ──────────────────────────────────────────────────────────────


@api_bp.route("/api/v1/products", methods=["GET", "POST"])
def products() -> tuple[Response, int]:
    return forward(f"{product_service_url()}/products", proxy_timeout())


@api_bp.route("/api/v1/products/count", methods=["GET"])
def products_count() -> tuple[Response, int]:
    return forward(f"{product_service_url()}/products/count", proxy_timeout())


@api_bp.route("/api/v1/products/name/<path:name>", methods=["GET"])
def products_by_name(name: str) -> tuple[Response, int]:
    return forward(f"{product_service_url()}/products/name/{name}", proxy_timeout())


@api_bp.route("/api/v1/products/<uuid:product_id>", methods=["GET", "PUT", "DELETE"])
def product_by_id(product_id: str) -> tuple[Response, int]:
    return forward(f"{product_service_url()}/products/{product_id}", proxy_timeout())


# ── Orders ────────────────────────────────────────────────────────────────


@api_bp.route("/api/v1/orders", methods=["GET", "POST"])
def orders() -> tuple[Response, int]:
    return forward(f"{order_service_url()}/orders", proxy_timeout())


@api_bp.route("/api/v1/orders/count", methods=["GET"])
def orders_count() -> tuple[Response, int]:
    return forward(f"{order_service_url()}/orders/count", proxy_timeout())


@api_bp.route("/api/v1/orders/<path:rest>", methods=["GET", "PUT", "DELETE"])
def order_by_external_id(rest: str) -> tuple[Response, int]:
    return forward(f"{order_service_url()}/orders/{rest}", proxy_timeout())
