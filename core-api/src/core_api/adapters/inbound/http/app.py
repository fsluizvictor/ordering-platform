from __future__ import annotations

from flask import Flask
from shared.http import create_service_app

from core_api.adapters.inbound.http.routes import api_bp
from core_api.config.settings import SERVICE_NAME


def create_app() -> Flask:
    app = create_service_app(SERVICE_NAME)
    app.register_blueprint(api_bp)
    return app
