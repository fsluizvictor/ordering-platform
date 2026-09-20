from __future__ import annotations

import os


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        msg = f"Missing required environment variable: {name}"
        raise RuntimeError(msg)
    return value


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def service_name(default: str) -> str:
    return os.getenv("SERVICE_NAME", default)


def log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO").upper()
