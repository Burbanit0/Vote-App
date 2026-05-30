"""
simulation_campaign.py — Flask delegate for the campaign route.

The compute worker now lives in api_v2.domain.simulations.campaign (Phase
4.5.b.3); this blueprint stays thin until app/ is deleted in the final teardown.
"""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from app.extensions import sim_limiter
from api_v2.domain.simulations.campaign import _campaign_worker

campaign_bp = Blueprint("simulation_campaign", __name__, url_prefix="/simulations")


@campaign_bp.route("/campaign", methods=["POST"])
@sim_limiter.limit("20 per minute")
def campaign_route() -> tuple[Response, int]:
    """Day-by-day campaign simulation. Thin delegate to _campaign_worker."""
    body, status = _campaign_worker(request.get_json(silent=True) or {})
    return jsonify(body), status
