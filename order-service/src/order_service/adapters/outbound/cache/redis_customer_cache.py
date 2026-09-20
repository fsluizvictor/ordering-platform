"""Redis Cache-Aside adapter for Customer data.

On cache HIT returns the cached CustomerData without contacting the Customer Service.
On cache MISS, delegates to the CustomerServiceClient, populates Redis with the result,
and returns the data.

Redis is not the source of truth. A missing key always falls back to the HTTP client.
"""

from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal  # noqa: F401  (imported for symmetry; not used directly here)

import redis

from order_service.adapters.outbound.external_services.customer_client import CustomerServiceClient
from order_service.domain.ports.customer_lookup import CustomerData, CustomerLookupPort

logger = logging.getLogger(__name__)

_KEY_PREFIX = "customer"


class RedisCustomerCache(CustomerLookupPort):
    """Cache-Aside implementation: Redis → HTTP client → Redis SET."""

    def __init__(
        self,
        redis_client: redis.Redis,
        http_client: CustomerServiceClient,
        ttl_seconds: int,
    ) -> None:
        self._redis = redis_client
        self._http = http_client
        self._ttl = ttl_seconds

    def get_customer(self, customer_id: uuid.UUID) -> CustomerData | None:
        key = f"{_KEY_PREFIX}:{customer_id}"
        try:
            cached = self._redis.get(key)
        except redis.RedisError as exc:
            # Cache unavailable — proceed with HTTP client (degraded mode).
            logger.warning(
                "Redis unavailable, falling back to HTTP client",
                extra={"customer_id": str(customer_id), "error": str(exc)},
            )
            cached = None

        if cached is not None:
            logger.debug("Customer cache HIT", extra={"customer_id": str(customer_id)})
            data = json.loads(cached)
            return CustomerData(
                id=uuid.UUID(data["id"]),
                name=data["name"],
                email=data["email"],
            )

        logger.debug("Customer cache MISS", extra={"customer_id": str(customer_id)})
        customer = self._http.get_customer(customer_id)

        if customer is not None:
            self._try_set_cache(key, customer)

        return customer

    def _try_set_cache(self, key: str, customer: CustomerData) -> None:
        payload = json.dumps(
            {"id": str(customer.id), "name": customer.name, "email": customer.email}
        )
        try:
            self._redis.set(key, payload, ex=self._ttl)
        except redis.RedisError as exc:
            # Cache write failure is non-fatal; data was fetched successfully.
            logger.warning(
                "Failed to populate customer cache",
                extra={"key": key, "error": str(exc)},
            )
