"""HTTP client for the Customer Service.

Used by the Order Worker on Redis cache misses.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
import uuid
from json import JSONDecodeError
from json import loads as json_loads

from order_service.domain.ports.customer_lookup import CustomerData

logger = logging.getLogger(__name__)


class CustomerServiceClient:
    """Fetches customer data from the Customer Service HTTP API."""

    def __init__(self, base_url: str) -> None:
        # Strip trailing slash for consistent URL construction.
        self._base_url = base_url.rstrip("/")

    def get_customer(self, customer_id: uuid.UUID) -> CustomerData | None:
        url = f"{self._base_url}/customers/{customer_id}"
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                body = response.read().decode()
                data = json_loads(body)
                return CustomerData(
                    id=uuid.UUID(data["id"]),
                    name=data["name"],
                    email=data["email"],
                )
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                logger.info(
                    "Customer not found in service",
                    extra={"customer_id": str(customer_id)},
                )
                return None
            logger.error(
                "Customer service HTTP error",
                extra={"customer_id": str(customer_id), "status": exc.code},
            )
            raise
        except (urllib.error.URLError, OSError, JSONDecodeError, KeyError) as exc:
            logger.error(
                "Customer service request failed",
                extra={"customer_id": str(customer_id), "error": str(exc)},
            )
            raise
