from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from ..models import Election, User, Candidate, db
from flask_jwt_extended import get_jwt_identity, jwt_required

election_bp = Blueprint('elections', __name__, url_prefix='/elections')

# Create an election 
@election_bp.route('/', methods=['POST'])
@jwt_required()
def create_election():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    voter_ids = data.get('voters', [])
    candidate_ids = data.get('candidates', [])

    current_user_identity = get_jwt_identity()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    if not isinstance(current_user_identity, dict) or 'id' not in current_user_identity:
        return jsonify({"msg": "Invalid JWT payload"}), 400

    current_user_id = current_user_identity['id']

    # Convert current_user_id to an integer if necessary
    current_user_id = int(current_user_id)

    new_election = Election(name=name, description=description, created_by=current_user_id)
    db.session.add(new_election)
    db.session.commit()

    # Add voters and candidates to the election
    for voter_id in voter_ids:
        voter = User.query.get(voter_id)
        if voter:
            new_election.voters.append(voter)

    for candidate_id in candidate_ids:
        candidate = Candidate.query.get(candidate_id)
        if candidate:
            new_election.candidates.append(candidate)

    db.session.commit()

    return jsonify({'message': 'Election created successfully', 'election_id': new_election.id}), 201

# Add the current user as a voter
@election_bp.route('/<int:election_id>/add_voter', methods=['POST'])
@jwt_required()
def add_voter_to_election(election_id):
    current_user_identity = get_jwt_identity()
    if not isinstance(current_user_identity, dict) or 'id' not in current_user_identity:
        return jsonify({"msg": "Invalid JWT payload"}), 400

    current_user_id = current_user_identity['id']
    # Convert current_user_id to an integer if necessary
    current_user_id = int(current_user_id)

    # Fetch the election and user from the database
    election = Election.query.get_or_404(election_id)
    user = User.query.get_or_404(current_user_id)

    # Check if the user is already a voter in the election
    if user in election.voters:
        return jsonify({'message': 'You are already a voter in this election.'}), 400

    # Add the user as a voter to the election
    election.voters.append(user)
    db.session.commit()

    return jsonify({'message': 'You have been added as a voter to the election.'}), 200

#Get all elections
@election_bp.route('/', methods=['GET'])
def get_elections():
    elections = Election.query.all()
    return jsonify([{
        'id': election.id,
        'name': election.name,
        'description': election.description,
        'created_by': election.created_by,
        'created_at': election.created_at,
        'candidates': [{
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name
        } for candidate in election.candidates],
        'voters': [{
            'id': voter.id,
            'username': voter.username
        } for voter in election.voters]
    } for election in elections])

# Get elelction by id
@election_bp.route('/<int:election_id>', methods=['GET'])
def get_election_by_id(election_id):
    election = Election.query.get(election_id)
    if not election:
        return jsonify({"msg":"No election found with this id"}), 404
    return jsonify({
        'id': election.id,
        'name': election.name,
        'description': election.description,
        'created_by': election.created_by,
        'created_at': election.created_at,
        'candidates': [{
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name
        } for candidate in election.candidates],
        'voters': [{
            'id': voter.id,
            'username': voter.username
        } for voter in election.voters]}), 200

## Get candidates for an election
@election_bp.route('/elections/<int:id>/candidates', methods=['GET'])
def get_candidates_for_election(id):
    election = Election.query.get_or_404(id)
    candidates = election.candidates
    return jsonify([{
        'id': candidate.id,
        'first_name': candidate.first_name,
        'last_name': candidate.last_name
    } for candidate in candidates])

## Get voters for an election
@election_bp.route('/elections/<int:id>/voters', methods=['GET'])
def get_voters_for_election(id):
    election = Election.query.get_or_404(id)
    voters = election.voters
    return jsonify([{
        'id': voter.id,
        'username': voter.username
    } for voter in voters])

## Get all election of a user
@election_bp.route('/users/<int:user_id>/elections', methods=['GET'])
@jwt_required()
def get_elections_for_user(user_id):
    # Ensure the authenticated user is accessing their own elections
    current_user_identity = get_jwt_identity()
    if not isinstance(current_user_identity, dict) or 'id' not in current_user_identity:
        return jsonify({"msg": "Invalid JWT payload"}), 400

    current_user_id = current_user_identity['id']
    # Convert current_user_id to an integer if necessary
    current_user_id = int(current_user_id)
    # if current_user_id != user_id:
    #     return jsonify({'message': 'Unauthorized access'}), 403

    # Fetch the user from the database
    user = User.query.get_or_404(user_id)

    # Fetch elections created by the user
    created_elections = Election.query.filter_by(created_by=user_id).all()

    # Fetch elections where the user is a voter
    voted_elections = user.elections.all()

    # Combine and deduplicate elections
    all_elections = list(set(created_elections + voted_elections))

    return jsonify([{
        'id': election.id,
        'name': election.name,
        'description': election.description,
        'created_by': election.created_by,
        'created_at': election.created_at
    } for election in all_elections])

## Delete an election
@election_bp.route('/<int:election_id>', methods=['DELETE'])
def delete_election(election_id):
    election = Election.query.get_or_404(election_id)
    db.session.delete(election)
    db.session.commit()

    return jsonify({'result':True})

@election_bp.route('/elections/<int:election_id>', methods=['PUT'])
def update_election(election_id):
    data = request.get_json()
    election = Election.query.get_or_404(election_id)

    election.name = data.get('name', election.name)
    election.description = data.get('description', election.description)

    db.session.commit()
    return jsonify({'message': 'Election updated successfully'})
