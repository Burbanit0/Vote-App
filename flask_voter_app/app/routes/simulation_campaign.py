"""
simulation_campaign.py — Day-by-day electoral campaign simulation route.
"""
from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, Response, jsonify, request

from app.utils.campaign_dynamics import simulate_campaign
from app.extensions import sim_limiter

campaign_bp = Blueprint("simulation_campaign", __name__, url_prefix="/simulations")


def _campaign_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Run a day-by-day campaign simulation. Pure-compute core shared by
    Flask + FastAPI. Returns (body, status)."""
    try:
        num_candidates = max(2, min(8,    int(data.get("num_candidates", 4))))
        num_voters     = max(10, min(2000, int(data.get("num_voters",    500))))
        num_days       = max(1, min(90,   int(data.get("num_days",       30))))
        method         = str(data.get("method", "plurality"))
        events         = data.get("events", [])
        seed_raw       = data.get("seed")
        seed           = int(seed_raw) if seed_raw is not None else None
    except (TypeError, ValueError) as exc:
        return {"error": f"Invalid parameter: {exc}"}, 400

    if not isinstance(events, list):
        return {"error": "'events' must be a list"}, 400

    try:
        result = simulate_campaign(
            num_candidates=num_candidates,
            num_voters=num_voters,
            num_days=num_days,
            events=events,
            method=method,
            seed=seed,
        )
        return result, 200
    except Exception as exc:
        return {"error": str(exc)}, 500


@campaign_bp.route("/campaign", methods=["POST"])
@sim_limiter.limit("20 per minute")
def campaign_route() -> tuple[Response, int]:
    """Day-by-day campaign simulation. Thin delegate to _campaign_worker."""
    body, status = _campaign_worker(request.get_json(silent=True) or {})
    return jsonify(body), status
