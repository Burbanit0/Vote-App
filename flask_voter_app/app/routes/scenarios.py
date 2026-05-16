from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models import SimulationScenario
from app.utils.response_utils import error_response, success_response
from app.extensions import sim_limiter

scenarios_bp = Blueprint("scenarios", __name__, url_prefix="/api/scenarios")


@scenarios_bp.route("/", methods=["GET"])
@jwt_required()
@sim_limiter.limit("60 per minute")
def list_scenarios():
    user_id = int(get_jwt_identity())
    scenarios = (
        SimulationScenario.query
        .filter_by(user_id=user_id)
        .order_by(SimulationScenario.created_at.desc())
        .all()
    )
    return jsonify([s.to_summary() for s in scenarios]), 200


@scenarios_bp.route("/", methods=["POST"])
@jwt_required()
@sim_limiter.limit("30 per minute")
def create_scenario():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return error_response("Name is required", 400)

    scenario = SimulationScenario(
        user_id=user_id,
        name=name,
        config=data.get("config", {}),
        results=data.get("results"),
    )
    db.session.add(scenario)
    db.session.commit()
    return jsonify(scenario.to_detail()), 201


@scenarios_bp.route("/<int:scenario_id>", methods=["GET"])
@jwt_required()
@sim_limiter.limit("60 per minute")
def get_scenario(scenario_id):
    user_id = int(get_jwt_identity())
    scenario = SimulationScenario.query.filter_by(
        id=scenario_id, user_id=user_id
    ).first()
    if not scenario:
        return error_response("Not found", 404)
    return jsonify(scenario.to_detail()), 200


@scenarios_bp.route("/<int:scenario_id>", methods=["DELETE"])
@jwt_required()
@sim_limiter.limit("30 per minute")
def delete_scenario(scenario_id):
    user_id = int(get_jwt_identity())
    scenario = SimulationScenario.query.filter_by(
        id=scenario_id, user_id=user_id
    ).first()
    if not scenario:
        return error_response("Not found", 404)
    db.session.delete(scenario)
    db.session.commit()
    return success_response({"message": "Deleted"}, 200)
