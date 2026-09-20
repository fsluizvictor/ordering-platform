"""Order Worker entrypoint.

Starts a blocking RabbitMQ consumer that processes OrderCreated events.

Each message is processed with a dedicated SQLAlchemy session so that
failures in one message do not affect subsequent ones.

Run with:
    python -m order_service.worker
"""

from __future__ import annotations

import logging

import redis as redis_lib
from shared.logging_setup import setup_logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from order_service.adapters.inbound.messaging.rabbitmq_consumer import RabbitMQConsumer
from order_service.adapters.outbound.cache.redis_customer_cache import RedisCustomerCache
from order_service.adapters.outbound.cache.redis_product_cache import RedisProductCache
from order_service.adapters.outbound.external_services.customer_client import CustomerServiceClient
from order_service.adapters.outbound.external_services.product_client import ProductServiceClient
from order_service.adapters.outbound.persistence.models import Base
from order_service.adapters.outbound.persistence.sqlalchemy_order_repository import (
    SQLAlchemyOrderRepository,
)
from order_service.application.services.order_processor import OrderProcessor
from order_service.config import settings

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging(settings.SERVICE_NAME, settings.log_level())

    logger.info("Order Worker starting")

    # Database
    engine = create_engine(settings.database_url(), pool_pre_ping=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Redis
    redis_client = redis_lib.from_url(settings.redis_url(), decode_responses=True)

    # External HTTP clients
    customer_client = CustomerServiceClient(settings.customer_service_url())
    product_client = ProductServiceClient(settings.product_service_url())

    # Cache-Aside adapters
    ttl = settings.cache_ttl_seconds()
    customer_lookup = RedisCustomerCache(redis_client, customer_client, ttl)
    product_lookup = RedisProductCache(redis_client, product_client, ttl)

    def processor_factory() -> OrderProcessor:
        """Return an OrderProcessor bound to a fresh session for each message."""
        session = session_factory()
        repo = SQLAlchemyOrderRepository(session)

        class _CommittingProcessor(OrderProcessor):
            """Wraps OrderProcessor to commit (or rollback) the session after process()."""

            def process(self, payload: dict[str, object]) -> None:  # type: ignore[override]
                try:
                    super().process(payload)
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

        return _CommittingProcessor(repo, customer_lookup, product_lookup)

    consumer = RabbitMQConsumer(
        rabbitmq_url=settings.rabbitmq_url(),
        processor_factory=processor_factory,
        prefetch=settings.prefetch(),
        max_retries=settings.max_retries(),
    )

    logger.info("Order Worker ready, starting consumer")
    consumer.run()


if __name__ == "__main__":
    main()
