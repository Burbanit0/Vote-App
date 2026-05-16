"""
simulation_campaign.py — Day-by-day electoral campaign simulation route.
"""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from app.utils.campaign_dynamics import simulate_campaign
from app.extensions import sim_limiter

campaign_bp = Blueprint("simulation_campaign", __name__, url_prefix="/simulations")


@campaign_bp.route("/campaign", methods=["POST"])
@sim_limiter.limit("20 per minute")
def campaign_route() -> tuple[Response, int]:
    """
    Run a day-by-day campaign simulation.

    Request body:
    {
        "num_candidates": 4,
        "num_voters":     500,
        "num_days":       30,
        "method":         "plurality",
        "events": [
            {"day": 5,  "type": "scandal",    "candidate": 0, "magnitude": 0.3},
            {"day": 12, "type": "good_debate", "candidate": 1, "magnitude": 0.2}
        ],
        "seed": null
    }

    Response (200):
    {
        "days":         [0, 1, …, 30],
        "daily_leader": ["Alice", "Bob", …],
        "daily_scores": {"Alice": [35.2, …], "Bob": [31.1, …], …},
        "events":       [...],
        "final_winner": "Alice",
        "lead_changes": 2,
        "candidates":   ["Alice", "Bob", "Carol", "Dave"]
    }
    """
    data = request.get_json() or {}

    try:
        num_candidates = max(2, min(8,    int(data.get("num_candidates", 4))))
        num_voters     = max(10, min(2000, int(data.get("num_voters",    500))))
        num_days       = max(1, min(90,   int(data.get("num_days",       30))))
        method         = str(data.get("method", "plurality"))
        events         = data.get("events", [])
        seed_raw       = data.get("seed")
        seed           = int(seed_raw) if seed_raw is not None else None
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid parameter: {exc}"}), 400

    if not isinstance(events, list):
        return jsonify({"error": "'events' must be a list"}), 400

    try:
        result = simulate_campaign(
            num_candidates=num_candidates,
            num_voters=num_voters,
            num_days=num_days,
            events=events,
            method=method,
            seed=seed,
        )
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
