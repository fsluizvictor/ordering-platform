from __future__ import annotations

from typing import Any

from flask import Response, jsonify

from shared.correlation import current_request_id


def error_body(code: str, message: str) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": current_request_id(),
        }
    }


def error_response(code: str, message: str, status: int) -> tuple[Response, int]:
    return jsonify(error_body(code, message)), status
