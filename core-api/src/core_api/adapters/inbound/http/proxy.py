"""HTTP proxy utilities.

Forwards inbound requests to internal services, propagating correlation IDs
and translating upstream error responses into the platform's standard format.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from flask import Response, g, request
from shared.correlation import CORRELATION_ID_HEADER, REQUEST_ID_HEADER
from shared.errors import error_body

logger = logging.getLogger(__name__)

# Headers from the original client that are safe to forward upstream.
_FORWARDED_REQUEST_HEADERS = frozenset(
    {
        "Content-Type",
        "Accept",
        "Authorization",
        "Idempotency-Key",
    }
)


def _build_upstream_headers() -> dict[str, str]:
    headers: dict[str, str] = {
        REQUEST_ID_HEADER: getattr(g, "request_id", ""),
        CORRELATION_ID_HEADER: getattr(g, "correlation_id", ""),
    }
    for header in _FORWARDED_REQUEST_HEADERS:
        value = request.headers.get(header)
        if value:
            headers[header] = value
    return headers


def forward(target_url: str, timeout: int = 10) -> tuple[Response, int]:
    """Forward the current Flask request to *target_url* and return the result.

    * 2xx/3xx responses are passed through transparently.
    * 4xx responses from the upstream service are forwarded as-is (the
      downstream service already produces the platform error shape).
    * 5xx or connection errors are collapsed into a safe INTERNAL_ERROR reply
      so that implementation details are never exposed to clients.
    """
    body: bytes | None = request.get_data() or None
    headers = _build_upstream_headers()

    # Build query string if present.
    query = request.query_string.decode()
    url = f"{target_url}?{query}" if query else target_url

    req = urllib.request.Request(
        url=url,
        data=body,
        headers=headers,
        method=request.method,
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data: bytes = resp.read()
            status: int = resp.status
            content_type: str = resp.headers.get("Content-Type", "application/json")
            return Response(data, status=status, content_type=content_type), status

    except urllib.error.HTTPError as exc:
        data = exc.read()
        if 400 <= exc.code < 500:
            # Forward 4xx responses from upstream unchanged — they already use
            # the platform error format.
            content_type = exc.headers.get("Content-Type", "application/json")
            return Response(data, status=exc.code, content_type=content_type), exc.code

        # 5xx from upstream: log and hide implementation details.
        logger.error(
            "Upstream returned %s for %s %s",
            exc.code,
            request.method,
            target_url,
            extra={
                "correlation_id": getattr(g, "correlation_id", None),
                "request_id": getattr(g, "request_id", None),
            },
        )
        payload: dict[str, Any] = error_body("INTERNAL_ERROR", "Internal server error")
        return Response(json.dumps(payload), status=500, content_type="application/json"), 500

    except Exception:
        logger.exception(
            "Proxy error for %s %s",
            request.method,
            target_url,
            extra={
                "correlation_id": getattr(g, "correlation_id", None),
                "request_id": getattr(g, "request_id", None),
            },
        )
        payload = error_body("INTERNAL_ERROR", "Internal server error")
        return Response(json.dumps(payload), status=500, content_type="application/json"), 500
