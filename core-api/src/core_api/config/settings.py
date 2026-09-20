from __future__ import annotations

from shared.env import env, env_int, log_level, service_name

SERVICE_NAME = service_name("core-api")


def customer_service_url() -> str:
    return env("CUSTOMER_SERVICE_URL", "http://customer-service:8001")


def product_service_url() -> str:
    return env("PRODUCT_SERVICE_URL", "http://product-service:8002")


def order_service_url() -> str:
    return env("ORDER_SERVICE_URL", "http://order-service:8003")


def port() -> int:
    return env_int("PORT", 8000)


def proxy_timeout() -> int:
    """Timeout in seconds for outbound proxy requests."""
    return env_int("PROXY_TIMEOUT", 10)


def log_level_setting() -> str:
    return log_level()
