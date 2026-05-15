from flask import jsonify
from typing import Any


def error_response(message: str, status_code: int = 400, details: Any = None) -> tuple:
    body = {"error": message, "code": status_code}
    if details:
        body["details"] = details
    return jsonify(body), status_code


def success_response(data: dict, status_code: int = 200) -> tuple:
    return jsonify(data), status_code
