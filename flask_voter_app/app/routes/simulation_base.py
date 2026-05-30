"""
simulation_base.py — Flask delegates for the core /simulations routes.

The compute workers now live in api_v2.domain.simulations.base (Phase 4.5.b.3);
this blueprint stays thin until app/ is deleted in the final teardown.
"""
from flask import Blueprint, jsonify, make_response, request

from app.extensions import sim_limiter
from api_v2.domain.simulations.base import (
    _calculate_utility_worker,
    _closest_candidate_worker,
    _simulate_candidates_worker,
    _simulate_utility_worker,
    _simulate_voters_worker,
    _simulate_votes_worker,
    _utility_matrix_worker,
    _voter_segments_worker,
)

simulation_base_bp = Blueprint("simulation_base", __name__, url_prefix="/simulations")


@simulation_base_bp.route("/", methods=["POST"])
@sim_limiter.limit("30 per minute")
def simulate_votes_route():
    body, status = _simulate_votes_worker(request.get_json(silent=True) or {})
    resp = make_response(jsonify(body), status)
    if "deprecation_warning" in body:
        resp.headers["X-Deprecation-Warning"] = body["deprecation_warning"]
    return resp


@simulation_base_bp.route("/simulate_voters", methods=["POST"])
@sim_limiter.limit("60 per minute")
def simulate_voters_repartitions():
    body, status = _simulate_voters_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/simulate_candidates", methods=["POST"])
@sim_limiter.limit("60 per minute")
def simulate_candidates_repartitions():
    body, status = _simulate_candidates_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/get_closest_candidate", methods=["POST"])
@sim_limiter.limit("60 per minute")
def get_closest_candidates():
    body, status = _closest_candidate_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/simulate_utility", methods=["POST"])
@sim_limiter.limit("30 per minute")
def simulate_utility():
    body, status = _simulate_utility_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/calculate_utility", methods=["POST"])
@sim_limiter.limit("60 per minute")
def calculate_single_utility():
    body, status = _calculate_utility_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/get_utility_matrix", methods=["POST"])
@sim_limiter.limit("30 per minute")
def get_utility_matrix():
    body, status = _utility_matrix_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/get_voter_segments", methods=["POST"])
@sim_limiter.limit("30 per minute")
def get_voter_segments():
    body, status = _voter_segments_worker(request.get_json(silent=True) or {})
    return jsonify(body), status
