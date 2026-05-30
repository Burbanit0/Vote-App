"""
simulation_compare.py — Flask delegates for the method-comparison routes.

The compute workers now live in api_v2.domain.simulations.compare (Phase
4.5.b.3); this blueprint stays thin until app/ is deleted in the final teardown.
"""
from flask import Blueprint, Response, jsonify, request

from app.extensions import sim_limiter
from api_v2.domain.simulations.compare import (
    _arrow_criteria_worker,
    _compare_methods_worker,
    _condorcet_matrix_worker,
    _ideology_map_worker,
    _manipulability_worker,
    _scenario_worker,
    _sensitivity_worker,
    _strategic_impact_worker,
    _vote_steps_worker,
)

simulation_compare_bp = Blueprint("simulation_compare", __name__, url_prefix="/simulations")


@simulation_compare_bp.route("/compare", methods=["POST"])
@sim_limiter.limit("30 per minute")
def compare_methods() -> tuple[Response, int]:
    body, status = _compare_methods_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_compare_bp.route("/strategic-impact", methods=["POST"])
@sim_limiter.limit("30 per minute")
def strategic_impact() -> tuple[Response, int]:
    body, status = _strategic_impact_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_compare_bp.route("/condorcet-matrix", methods=["POST"])
@sim_limiter.limit("30 per minute")
def condorcet_matrix_route() -> tuple[Response, int]:
    body, status = _condorcet_matrix_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_compare_bp.route("/sensitivity", methods=["POST"])
@sim_limiter.limit("30 per minute")
def sensitivity_analysis() -> tuple[Response, int]:
    body, status = _sensitivity_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_compare_bp.route("/arrow-criteria", methods=["POST"])
@sim_limiter.limit("30 per minute")
def arrow_criteria_route() -> tuple[Response, int]:
    body, status = _arrow_criteria_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_compare_bp.route("/scenario", methods=["POST"])
@sim_limiter.limit("30 per minute")
def run_scenario() -> tuple[Response, int]:
    body, status = _scenario_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_compare_bp.route("/manipulability", methods=["GET"])
@sim_limiter.limit("30 per minute")
def manipulability_analysis() -> tuple[Response, int]:
    body, status = _manipulability_worker(request.args.to_dict())
    return jsonify(body), status


@simulation_compare_bp.route("/vote-steps", methods=["POST"])
@sim_limiter.limit("30 per minute")
def vote_steps() -> tuple[Response, int]:
    body, status = _vote_steps_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_compare_bp.route("/ideology-map", methods=["POST"])
@sim_limiter.limit("30 per minute")
def ideology_map() -> tuple[Response, int]:
    body, status = _ideology_map_worker(request.get_json(silent=True) or {})
    return jsonify(body), status
