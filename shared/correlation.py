from __future__ import annotations

import uuid

from flask import Flask, Response, g, request

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


def init_correlation(app: Flask) -> None:
    @app.before_request
    def assign_ids() -> None:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id
        g.request_id = request_id
        g.correlation_id = correlation_id

    @app.after_request
    def set_headers(response: Response) -> Response:
        response.headers[REQUEST_ID_HEADER] = getattr(g, "request_id", "")
        response.headers[CORRELATION_ID_HEADER] = getattr(g, "correlation_id", "")
        return response


def current_request_id() -> str | None:
    return getattr(g, "request_id", None)
