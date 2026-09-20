from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from flask import Flask, jsonify
from sqlalchemy import create_engine, text

from shared.correlation import init_correlation
from shared.errors import error_response

logger = logging.getLogger(__name__)

ReadyCheck = Callable[[], tuple[bool, str]]


def check_postgres(database_url: str) -> tuple[bool, str]:
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "ok"
    except Exception:  # noqa: BLE001
        logger.debug("PostgreSQL readiness check failed", exc_info=True)
        return False, "unavailable"


def create_service_app(
    service_name: str,
    *,
    ready_checks: dict[str, ReadyCheck] | None = None,
) -> Flask:
    # Use the shared module as Flask's import_name so Flask can always resolve
    # its root path.  Service names like "product-service" contain hyphens and
    # are not valid Python identifiers, which causes Flask 3.x to raise
    # RuntimeError when it cannot import the name to find the root path.
    app = Flask(__name__)
    app.config["SERVICE_NAME"] = service_name
    init_correlation(app)
    checks = ready_checks or {}

    @app.get("/health")
    def health() -> tuple:
        return (
            jsonify(
                {
                    "status": "ok",
                    "service": service_name,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            ),
            200,
        )

    @app.get("/ready")
    def ready() -> tuple:
        results: dict[str, str] = {}
        healthy = True
        for name, check in checks.items():
            ok, detail = check()
            results[name] = detail
            healthy = healthy and ok
        body = {"status": "ok" if healthy else "degraded", "checks": results}
        return jsonify(body), 200 if healthy else 503

    @app.errorhandler(404)
    def not_found(_error: Exception) -> tuple:
        return error_response("RESOURCE_NOT_FOUND", "Not found", 404)

    @app.errorhandler(500)
    def internal(_error: Exception) -> tuple:
        return error_response("INTERNAL_ERROR", "Internal server error", 500)

    return app
