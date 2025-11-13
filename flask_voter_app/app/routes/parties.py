# app/api/parties.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..services.party_service import PartyService

party_bp = Blueprint('parties', __name__, url_prefix='/parties')


@party_bp.route('/', methods=['GET'])
def get_all_parties():
    """Get all political parties"""
    result = PartyService.get_all_parties()
    return jsonify(result)


@party_bp.route('/', methods=['POST'])
@jwt_required()
def create_party():
    """Create a new political party"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    result = PartyService.create_party(name, description)
    return jsonify(result), 201


@party_bp.route('/<int:party_id>', methods=['GET'])
def get_party(party_id):
    """Get a specific party"""
    result = PartyService.get_party(party_id)
    return jsonify(result)


@party_bp.route('/<int:party_id>', methods=['PUT'])
@jwt_required()
def update_party(party_id):
    """Update a political party"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    result = PartyService.update_party(party_id, name, description)
    return jsonify(result)


# Assign a user to a party
@party_bp.route('/<int:user_id>/assign-party', methods=['POST'])
@jwt_required()
def assign_user_to_party(user_id):
    data = request.get_json()
    party_id = data.get('party_id')

    result = PartyService.assign_user_to_party(user_id, party_id)
    return jsonify(result)


# Remove a user from a party
@party_bp.route('/<int:user_id>/remove-party', methods=['POST'])
@jwt_required()
def remove_user_from_party(user_id):
    result = PartyService.remove_user_from_party(user_id)
    return jsonify(result)


# Get all users in a party
@party_bp.route('/<int:party_id>/users', methods=['GET'])
@jwt_required()
def get_party_users(party_id):
    result = PartyService.get_party_users(party_id)
    return jsonify(result)
