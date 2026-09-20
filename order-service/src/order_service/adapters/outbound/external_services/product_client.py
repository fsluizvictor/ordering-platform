"""HTTP client for the Product Service.

Used by the Order Worker on Redis cache misses.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
import uuid
from decimal import Decimal
from json import JSONDecodeError
from json import loads as json_loads

from order_service.domain.ports.product_lookup import ProductData

logger = logging.getLogger(__name__)


class ProductServiceClient:
    """Fetches product data from the Product Service HTTP API."""

    def __init__(self, base_url: str) -> None:
        # Strip trailing slash for consistent URL construction.
        self._base_url = base_url.rstrip("/")

    def get_product(self, product_id: uuid.UUID) -> ProductData | None:
        url = f"{self._base_url}/products/{product_id}"
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                body = response.read().decode()
                data = json_loads(body)
                return ProductData(
                    id=uuid.UUID(data["id"]),
                    name=data["name"],
                    price=Decimal(str(data["price"])),
                    stock=int(data["stock"]),
                )
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                logger.info(
                    "Product not found in service",
                    extra={"product_id": str(product_id)},
                )
                return None
            logger.error(
                "Product service HTTP error",
                extra={"product_id": str(product_id), "status": exc.code},
            )
            raise
        except (urllib.error.URLError, OSError, JSONDecodeError, KeyError) as exc:
            logger.error(
                "Product service request failed",
                extra={"product_id": str(product_id), "error": str(exc)},
            )
            raise
