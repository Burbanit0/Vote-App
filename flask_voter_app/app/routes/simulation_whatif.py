"""
simulation_whatif.py — Flask delegate for the what-if route.

The compute worker now lives in api_v2.domain.simulations.whatif (Phase
4.5.b.3); this blueprint stays thin until app/ is deleted in the final teardown.
"""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from app.extensions import sim_limiter
from api_v2.domain.simulations.whatif import _what_if_worker

whatif_bp = Blueprint("simulation_whatif", __name__, url_prefix="/simulations")


@whatif_bp.route("/what-if", methods=["POST"])
@sim_limiter.limit("20 per minute")
def what_if() -> tuple[Response, int]:
    """Compare winners across methods while varying a single parameter.
    Thin delegate to _what_if_worker."""
    body, status = _what_if_worker(request.get_json(silent=True) or {})
    return jsonify(body), status
