from __future__ import annotations

from shared.env import env, env_int, log_level as env_log_level, service_name

SERVICE_NAME = service_name("customer-service")


def database_url() -> str:
    return env("CUSTOMER_DATABASE_URL")


def port() -> int:
    return env_int("PORT", 8001)


def log_level() -> str:
    return env_log_level()
