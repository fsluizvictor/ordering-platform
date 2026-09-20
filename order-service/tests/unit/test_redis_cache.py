"""Unit tests for Redis Cache-Aside adapters.

Redis and HTTP clients are replaced with mocks so these tests run offline.
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from unittest.mock import MagicMock

from order_service.adapters.outbound.cache.redis_customer_cache import RedisCustomerCache
from order_service.adapters.outbound.cache.redis_product_cache import RedisProductCache
from order_service.adapters.outbound.external_services.customer_client import CustomerServiceClient
from order_service.adapters.outbound.external_services.product_client import ProductServiceClient
from order_service.domain.ports.customer_lookup import CustomerData
from order_service.domain.ports.product_lookup import ProductData

_CUSTOMER_ID = uuid.uuid4()
_PRODUCT_ID = uuid.uuid4()
_TTL = 300


# ── Customer cache ────────────────────────────────────────────────────────────


class TestRedisCustomerCache:
    def _make_cache(
        self,
        cached_value: str | None = None,
        http_result: CustomerData | None = None,
    ) -> tuple[RedisCustomerCache, MagicMock, MagicMock]:
        redis_client = MagicMock()
        redis_client.get.return_value = cached_value

        http_client = MagicMock(spec=CustomerServiceClient)
        http_client.get_customer.return_value = http_result

        cache = RedisCustomerCache(redis_client, http_client, _TTL)
        return cache, redis_client, http_client

    def test_cache_hit_returns_data_without_calling_http(self) -> None:
        payload = json.dumps(
            {"id": str(_CUSTOMER_ID), "name": "Alice", "email": "alice@example.com"}
        )
        cache, _, http_client = self._make_cache(cached_value=payload)

        result = cache.get_customer(_CUSTOMER_ID)

        assert result is not None
        assert result.name == "Alice"
        http_client.get_customer.assert_not_called()

    def test_cache_miss_calls_http_client(self) -> None:
        customer = CustomerData(id=_CUSTOMER_ID, name="Bob", email="bob@example.com")
        cache, redis_client, http_client = self._make_cache(cached_value=None, http_result=customer)

        result = cache.get_customer(_CUSTOMER_ID)

        assert result == customer
        http_client.get_customer.assert_called_once_with(_CUSTOMER_ID)

    def test_cache_miss_populates_redis(self) -> None:
        customer = CustomerData(id=_CUSTOMER_ID, name="Bob", email="bob@example.com")
        cache, redis_client, _ = self._make_cache(cached_value=None, http_result=customer)

        cache.get_customer(_CUSTOMER_ID)

        redis_client.set.assert_called_once()
        _, call_kwargs = redis_client.set.call_args
        assert call_kwargs.get("ex") == _TTL

    def test_not_found_customer_returns_none_without_caching(self) -> None:
        cache, redis_client, _ = self._make_cache(cached_value=None, http_result=None)

        result = cache.get_customer(_CUSTOMER_ID)

        assert result is None
        redis_client.set.assert_not_called()

    def test_redis_error_falls_back_to_http(self) -> None:
        import redis

        redis_client = MagicMock()
        redis_client.get.side_effect = redis.RedisError("connection refused")

        customer = CustomerData(id=_CUSTOMER_ID, name="Alice", email="alice@example.com")
        http_client = MagicMock(spec=CustomerServiceClient)
        http_client.get_customer.return_value = customer

        cache = RedisCustomerCache(redis_client, http_client, _TTL)
        result = cache.get_customer(_CUSTOMER_ID)

        assert result == customer


# ── Product cache ─────────────────────────────────────────────────────────────


class TestRedisProductCache:
    def _make_cache(
        self,
        cached_value: str | None = None,
        http_result: ProductData | None = None,
    ) -> tuple[RedisProductCache, MagicMock, MagicMock]:
        redis_client = MagicMock()
        redis_client.get.return_value = cached_value

        http_client = MagicMock(spec=ProductServiceClient)
        http_client.get_product.return_value = http_result

        cache = RedisProductCache(redis_client, http_client, _TTL)
        return cache, redis_client, http_client

    def test_cache_hit_returns_data_without_calling_http(self) -> None:
        payload = json.dumps(
            {"id": str(_PRODUCT_ID), "name": "Widget", "price": "9.99", "stock": 50}
        )
        cache, _, http_client = self._make_cache(cached_value=payload)

        result = cache.get_product(_PRODUCT_ID)

        assert result is not None
        assert result.price == Decimal("9.99")
        assert result.stock == 50
        http_client.get_product.assert_not_called()

    def test_cache_miss_calls_http_client(self) -> None:
        product = ProductData(id=_PRODUCT_ID, name="Widget", price=Decimal("9.99"), stock=50)
        cache, _, http_client = self._make_cache(cached_value=None, http_result=product)

        result = cache.get_product(_PRODUCT_ID)

        assert result == product
        http_client.get_product.assert_called_once_with(_PRODUCT_ID)

    def test_cache_miss_populates_redis(self) -> None:
        product = ProductData(id=_PRODUCT_ID, name="Widget", price=Decimal("9.99"), stock=50)
        cache, redis_client, _ = self._make_cache(cached_value=None, http_result=product)

        cache.get_product(_PRODUCT_ID)

        redis_client.set.assert_called_once()
        _, call_kwargs = redis_client.set.call_args
        assert call_kwargs.get("ex") == _TTL

    def test_not_found_product_returns_none_without_caching(self) -> None:
        cache, redis_client, _ = self._make_cache(cached_value=None, http_result=None)

        result = cache.get_product(_PRODUCT_ID)

        assert result is None
        redis_client.set.assert_not_called()

    def test_redis_error_falls_back_to_http(self) -> None:
        import redis

        redis_client = MagicMock()
        redis_client.get.side_effect = redis.RedisError("connection refused")

        product = ProductData(id=_PRODUCT_ID, name="Widget", price=Decimal("9.99"), stock=50)
        http_client = MagicMock(spec=ProductServiceClient)
        http_client.get_product.return_value = product

        cache = RedisProductCache(redis_client, http_client, _TTL)
        result = cache.get_product(_PRODUCT_ID)

        assert result == product
