# app/api/parties.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Party
from app import db

bp = Blueprint('parties', __name__, url_prefix='/parties')


@bp.route('/', methods=['GET'])
def get_all_parties():
    """Get all political parties"""
    parties = Party.query.all()
    return jsonify([{
        'id': party.id,
        'name': party.name,
        'description': party.description
    } for party in parties])


@bp.route('/', methods=['POST'])
@jwt_required()
def create_party():
    """Create a new political party"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({'message': 'Name is required'}), 400

    if Party.query.filter_by(name=name).first():
        return jsonify({'message': 'Party with this name already exists'}), 400

    party = Party(
        name=name,
        description=description
    )

    db.session.add(party)
    db.session.commit()

    return jsonify({
        'id': party.id,
        'name': party.name,
        'description': party.description
    }), 201


@bp.route('/<int:party_id>', methods=['GET'])
def get_party(party_id):
    """Get a specific party"""
    party = Party.query.get_or_404(party_id)
    return jsonify({
        'id': party.id,
        'name': party.name,
        'description': party.description
    })


@bp.route('/<int:party_id>', methods=['PUT'])
@jwt_required()
def update_party(party_id):
    """Update a political party"""
    party = Party.query.get_or_404(party_id)
    data = request.get_json()

    name = data.get('name')
    description = data.get('description')

    if name:
        if name != party.name and Party.query.filter_by(name=name).first():
            return jsonify({
                'message': 'Party with this name already exists'}), 400
        party.name = name

    if description is not None:
        party.description = description

    db.session.commit()

    return jsonify({
        'id': party.id,
        'name': party.name,
        'description': party.description
    })
