# app/api/parties.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Party, User
from app import db

party_bp = Blueprint('parties', __name__, url_prefix='/parties')


@party_bp.route('/', methods=['GET'])
def get_all_parties():
    """Get all political parties"""
    parties = Party.query.all()
    return jsonify([{
        'id': party.id,
        'name': party.name,
        'description': party.description
    } for party in parties])


@party_bp.route('/', methods=['POST'])
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


@party_bp.route('/<int:party_id>', methods=['GET'])
def get_party(party_id):
    """Get a specific party"""
    party = Party.query.get_or_404(party_id)
    return jsonify({
        'id': party.id,
        'name': party.name,
        'description': party.description
    })


@party_bp.route('/<int:party_id>', methods=['PUT'])
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


# Assign a user to a party
@party_bp.route('/<int:user_id>/assign-party', methods=['POST'])
@jwt_required()
def assign_user_to_party(user_id):
    data = request.get_json()
    party_id = data.get('party_id')

    if not party_id:
        return jsonify({'message': 'Party ID is required'}), 400

    user = User.query.get_or_404(user_id)
    party = Party.query.get_or_404(party_id)

    # For one-to-one relationship
    user.party_id = party_id
    db.session.commit()

    # For many-to-many relationship
    # if party not in user.parties:
    #     user.parties.append(party)
    #     db.session.commit()

    return jsonify({
        'message': 'User assigned to party successfully',
        'user_id': user.id,
        'party_id': party.id
    })


# Remove a user from a party
@party_bp.route('/<int:user_id>/remove-party', methods=['POST'])
@jwt_required()
def remove_user_from_party(user_id):
    user = User.query.get_or_404(user_id)

    # For one-to-one relationship
    user.party_id = None
    db.session.commit()

    # For many-to-many relationship
    # user.parties.clear()
    # db.session.commit()

    return jsonify({
        'message': 'User removed from party successfully',
        'user_id': user.id
    })


# Get all users in a party
@party_bp.route('/<int:party_id>/users', methods=['GET'])
@jwt_required()
def get_party_users(party_id):
    party = Party.query.get_or_404(party_id)
    users = party.members  # For one-to-many
    # users = party.users.all()  # For many-to-many

    return jsonify([{
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    } for user in users])
