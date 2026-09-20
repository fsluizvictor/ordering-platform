from __future__ import annotations

from flask import Flask
from shared.http import check_postgres, create_service_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from order_service.adapters.inbound.http.routes import order_bp
from order_service.adapters.outbound.persistence.models import Base
from order_service.config.settings import SERVICE_NAME, database_url, rabbitmq_url


def create_app() -> Flask:
    app = create_service_app(
        SERVICE_NAME,
        ready_checks={"postgres": lambda: check_postgres(database_url())},
    )

    engine = create_engine(database_url(), pool_pre_ping=True)
    # Create tables if they do not exist (idempotent in development).
    # Migrations would replace this in production.
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    app.config["SESSION_FACTORY"] = session_factory
    app.config["RABBITMQ_URL"] = rabbitmq_url()

    app.register_blueprint(order_bp)

    @app.teardown_appcontext
    def close_session(exc: BaseException | None) -> None:
        from flask import g

        session = g.pop("db_session", None)
        if session is not None:
            if exc is None:
                session.commit()
            else:
                session.rollback()
            session.close()

    return app
