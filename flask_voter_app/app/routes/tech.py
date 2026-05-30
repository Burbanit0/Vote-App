"""
tech.py — Flask delegates for the tech-democracy demos.

The compute workers now live in api_v2.domain.tech (Phase 4.5.b.3); this
blueprint stays thin until app/ is deleted in the final teardown.
"""
from flask import Blueprint, Response, current_app, jsonify, request

from app.extensions import sim_limiter
from api_v2.domain.tech import (
    _e2e_demo_worker,
    _polis_simulation_worker,
    _polis_with_candidates_worker,
)

tech_bp = Blueprint("tech", __name__, url_prefix="/api/tech")


@tech_bp.route("/e2e-demo", methods=["POST"])
@sim_limiter.limit("20 per minute")
def e2e_demo() -> tuple[Response, int]:
    """POST /api/tech/e2e-demo — End-to-end verifiable voting demo."""
    try:
        body, status_code = _e2e_demo_worker(request.get_json() or {})
        return jsonify(body), status_code
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("e2e_demo() crashed")
        return jsonify({"error": f"Internal error: {exc}"}), 500


@tech_bp.route("/polis-simulation", methods=["POST"])
@sim_limiter.limit("10 per minute")
def polis_simulation() -> tuple[Response, int]:
    """POST /api/tech/polis-simulation — Pol.is consensus clustering."""
    try:
        body, status_code = _polis_simulation_worker(request.get_json() or {})
        return jsonify(body), status_code
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("polis_simulation() crashed")
        return jsonify({"error": f"Internal error: {exc}"}), 500


@tech_bp.route("/polis", methods=["POST"])
@sim_limiter.limit("5 per minute")
def polis_with_candidates() -> tuple[Response, int]:
    """POST /api/tech/polis — Pol.is clustering + classical election comparison."""
    try:
        body, status_code = _polis_with_candidates_worker(request.get_json() or {})
        return jsonify(body), status_code
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("polis_with_candidates() crashed")
        return jsonify({"error": f"Internal error: {exc}"}), 500
