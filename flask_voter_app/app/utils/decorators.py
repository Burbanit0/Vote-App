from functools import wraps
from typing import Any, Callable, Dict, Tuple

from eventlet import tpool
from flask import current_app, jsonify, request, Response
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.models import User
from app.utils.response_utils import error_response


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or user.role != "Admin":
            return error_response("Admin access required", 403)

        return fn(*args, **kwargs)

    return wrapper


# ── heavy_endpoint ───────────────────────────────────────────────────────────
# Wraps a compute-bound "worker" function so the heavy CPU work runs in a real
# OS thread via eventlet.tpool. The eventlet event loop stays free to serve
# WebSockets and concurrent HTTP requests — without this, a single slow
# simulation blocks every other request until it returns.
#
# Worker contract:
#   worker(data: dict) -> tuple[dict, int]
#       data:   the parsed JSON body of the request
#       return: (response_body, http_status)
#
# Usage:
#   @election_bp.route("/combined-effects", methods=["POST"])
#   @sim_limiter.limit("5 per minute")
#   @heavy_endpoint
#   def combined_effects():
#       return _combined_effects_worker
#
# The decorated view returns a callable that yields the worker. This indirection
# keeps the worker function importable for unit tests (test directly with a dict
# in / dict out — no Flask app needed).

WorkerFn = Callable[[Dict[str, Any]], Tuple[Dict[str, Any], int]]
ViewFn   = Callable[[], WorkerFn]


def heavy_endpoint(view: ViewFn) -> Callable[[], Tuple[Response, int]]:
    """Decorator: run the worker yielded by `view` inside eventlet's tpool."""
    @wraps(view)
    def wrapped() -> Tuple[Response, int]:
        worker = view()
        data = request.get_json() or {}
        try:
            body, status = tpool.execute(worker, data)
            return jsonify(body), status
        except Exception as exc:
            current_app.logger.exception("%s crashed", getattr(worker, "__name__", "worker"))
            return jsonify({"error": f"Internal error: {exc}"}), 500
    return wrapped
