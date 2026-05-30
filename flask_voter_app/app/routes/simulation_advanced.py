"""
simulation_advanced.py — Flask delegates for the advanced analysis routes.

The compute workers now live in api_v2.domain.simulations.advanced (Phase
4.5.b.3); this blueprint stays thin until app/ is deleted in the final teardown.
"""
from flask import Blueprint, Response, jsonify, request

from app.extensions import sim_limiter
from api_v2.domain.simulations.advanced import (
    _bandwagon_worker,
    _blank_contagion_worker,
    _blank_history_worker,
    _constitutional_scenario_worker,
    _monte_carlo_worker,
    _multiwinner_worker,
    _real_election_worker,
    _real_elections_list_worker,
)

simulation_advanced_bp = Blueprint("simulation_advanced", __name__, url_prefix="/simulations")


@simulation_advanced_bp.route("/bandwagon", methods=["POST"])
@sim_limiter.limit("30 per minute")
def bandwagon_route() -> tuple[Response, int]:
    body, status = _bandwagon_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_advanced_bp.route("/monte-carlo", methods=["POST"])
@sim_limiter.limit("10 per minute")
def monte_carlo_route() -> tuple[Response, int]:
    body, status = _monte_carlo_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_advanced_bp.route("/multiwinner", methods=["POST"])
@sim_limiter.limit("30 per minute")
def multiwinner_route() -> tuple[Response, int]:
    body, status = _multiwinner_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_advanced_bp.route("/real-elections", methods=["GET"])
@sim_limiter.limit("60 per minute")
def real_elections_list() -> tuple[Response, int]:
    body, status = _real_elections_list_worker({})
    return jsonify(body), status


@simulation_advanced_bp.route("/blank-history", methods=["GET"])
@sim_limiter.limit("60 per minute")
def blank_history_route() -> tuple[Response, int]:
    body, status = _blank_history_worker(request.args.to_dict())
    return jsonify(body), status


@simulation_advanced_bp.route("/real-election", methods=["POST"])
@sim_limiter.limit("30 per minute")
def real_election_analyze() -> tuple[Response, int]:
    body, status = _real_election_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_advanced_bp.route("/constitutional-scenario", methods=["POST"])
@sim_limiter.limit("20 per minute")
def constitutional_scenario() -> tuple[Response, int]:
    body, status = _constitutional_scenario_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_advanced_bp.route("/blank-contagion", methods=["POST"])
@sim_limiter.limit("20 per minute")
def blank_contagion_route() -> tuple[Response, int]:
    body, status = _blank_contagion_worker(request.get_json(silent=True) or {})
    return jsonify(body), status
