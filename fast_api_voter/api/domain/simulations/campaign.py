"""
api.domain.simulations.campaign — day-by-day campaign simulation worker.

Relocated from app/routes/simulation_campaign.py (Phase 4.5.b.3). Flask-free.
"""
from __future__ import annotations

from typing import Any, Dict

from api.engine.utils.campaign_dynamics import simulate_campaign


def _campaign_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Run a day-by-day campaign simulation. Returns (body, status)."""
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
