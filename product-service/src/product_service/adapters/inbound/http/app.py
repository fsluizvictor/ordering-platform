from __future__ import annotations

from flask import Flask

from product_service.config.settings import SERVICE_NAME, database_url
from shared.http import check_postgres, create_service_app


def create_app() -> Flask:
    return create_service_app(
        SERVICE_NAME,
        ready_checks={"postgres": lambda: check_postgres(database_url())},
    )
