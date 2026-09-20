from __future__ import annotations

from shared.env import env, env_int, service_name
from shared.env import log_level as env_log_level

SERVICE_NAME = service_name("order-service")

EXCHANGE_ORDERS = "orders"
EXCHANGE_DLX = "orders.dlx"
ROUTING_KEY_CREATED = "order.created"
QUEUE_CREATED = "orders.created"
QUEUE_DLQ = "orders.created.dlq"


def database_url() -> str:
    return env("ORDER_DATABASE_URL")


def rabbitmq_url() -> str:
    return env("RABBITMQ_URL")


def port() -> int:
    return env_int("PORT", 8003)


def prefetch() -> int:
    return env_int("RABBITMQ_PREFETCH", 1)


def max_retries() -> int:
    return env_int("ORDER_MAX_RETRIES", 3)


def log_level() -> str:
    return env_log_level()
