"""Redis Cache-Aside adapter for Product data.

On cache HIT returns the cached ProductData without contacting the Product Service.
On cache MISS, delegates to the ProductServiceClient, populates Redis with the result,
and returns the data.

Redis is not the source of truth. A missing key always falls back to the HTTP client.
"""

from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal

import redis

from order_service.adapters.outbound.external_services.product_client import ProductServiceClient
from order_service.domain.ports.product_lookup import ProductData, ProductLookupPort

logger = logging.getLogger(__name__)

_KEY_PREFIX = "product"


class RedisProductCache(ProductLookupPort):
    """Cache-Aside implementation: Redis → HTTP client → Redis SET."""

    def __init__(
        self,
        redis_client: redis.Redis,
        http_client: ProductServiceClient,
        ttl_seconds: int,
    ) -> None:
        self._redis = redis_client
        self._http = http_client
        self._ttl = ttl_seconds

    def get_product(self, product_id: uuid.UUID) -> ProductData | None:
        key = f"{_KEY_PREFIX}:{product_id}"
        try:
            cached = self._redis.get(key)
        except redis.RedisError as exc:
            # Cache unavailable — proceed with HTTP client (degraded mode).
            logger.warning(
                "Redis unavailable, falling back to HTTP client",
                extra={"product_id": str(product_id), "error": str(exc)},
            )
            cached = None

        if cached is not None:
            logger.debug("Product cache HIT", extra={"product_id": str(product_id)})
            data = json.loads(cached)
            return ProductData(
                id=uuid.UUID(data["id"]),
                name=data["name"],
                price=Decimal(data["price"]),
                stock=int(data["stock"]),
            )

        logger.debug("Product cache MISS", extra={"product_id": str(product_id)})
        product = self._http.get_product(product_id)

        if product is not None:
            self._try_set_cache(key, product)

        return product

    def _try_set_cache(self, key: str, product: ProductData) -> None:
        payload = json.dumps(
            {
                "id": str(product.id),
                "name": product.name,
                "price": str(product.price),
                "stock": product.stock,
            }
        )
        try:
            self._redis.set(key, payload, ex=self._ttl)
        except redis.RedisError as exc:
            # Cache write failure is non-fatal; data was fetched successfully.
            logger.warning(
                "Failed to populate product cache",
                extra={"key": key, "error": str(exc)},
            )
