from __future__ import annotations

from collections.abc import Callable

from flask import Flask, g
from shared.http import check_postgres, create_service_app
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from product_service.adapters.inbound.http.routes import product_bp
from product_service.adapters.outbound.persistence.models import Base
from product_service.config.settings import SERVICE_NAME, database_url


def _make_session_factory(db_url: str) -> Callable[[], Session]:
    """Create the SQLAlchemy engine, run DDL, and return a session factory."""
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def create_app(session_factory: Callable[[], Session] | None = None) -> Flask:
    app = create_service_app(
        SERVICE_NAME,
        # database_url() is inside a lambda — evaluated lazily only on /ready.
        ready_checks={"postgres": lambda: check_postgres(database_url())},
    )

    factory = session_factory or _make_session_factory(database_url())
    app.config["SESSION_FACTORY"] = factory

    @app.teardown_request
    def close_db(exc: BaseException | None) -> None:
        """Commit on success, roll back on error, always close the session."""
        session: Session | None = g.pop("db_session", None)
        if session is not None:
            if exc is None:
                session.commit()
            else:
                session.rollback()
            session.close()

    app.register_blueprint(product_bp)
    return app
