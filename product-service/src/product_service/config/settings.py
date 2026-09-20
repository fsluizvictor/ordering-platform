from __future__ import annotations

from shared.env import env, env_int, log_level as env_log_level, service_name

SERVICE_NAME = service_name("product-service")


def database_url() -> str:
    return env("PRODUCT_DATABASE_URL")


def port() -> int:
    return env_int("PORT", 8002)


def log_level() -> str:
    return env_log_level()
