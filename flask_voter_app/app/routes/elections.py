from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from flask_jwt_extended import get_jwt_identity, jwt_required
from app import db
from ..models import Election, User, ElectionRole, user_election_roles
from ..services.participation_service import ParticipationService
from app.utils.decorators import (
    admin_required,
    # election_organizer_required,
    candidate_eligible_required,
    organizer_eligible_required,
    not_candidate_in_election,
    not_organizer_in_election
)
# from app import redis_client
# import json

election_bp = Blueprint('elections', __name__, url_prefix='/elections')


@election_bp.route('/', methods=['GET'])
def get_all_elections():
    """Get all elections"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Get search term
    search_term = request.args.get('search', '', type=str)

    query = Election.query
    if search_term:
        query = query.filter(
            or_(
                Election.name.ilike(f'%{search_term}%'),
                Election.description.ilike(f'%{search_term}%')
            )
        )
    paginated_elections = query.paginate(page=page, per_page=per_page,
                                         error_out=False)

    return jsonify({
        'elections': [{
            'id': election.id,
            'name': election.name,
            'description': election.description,
            'created_at': election.created_at.isoformat()
            if election.created_at else None
        } for election in paginated_elections.items],
        'total': paginated_elections.total,
        'pages': paginated_elections.pages,
        'current_page': paginated_elections.page,
        'per_page': paginated_elections.per_page
    })


@election_bp.route('/', methods=['POST'])
@jwt_required()
@organizer_eligible_required
@not_candidate_in_election
def create_election():
    """Create a new election"""
    current_user_id = get_jwt_identity()

    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    created_at = data.get('created_at')

    if not name:
        return jsonify({'message': 'Name is required'}), 400

    election = Election(
        name=name,
        description=description,
        created_by=current_user_id,
        created_at=created_at
    )

    # Add the creator as an organizer
    db.session.execute(
        user_election_roles.insert().values(
            user_id=current_user_id,
            election_id=election.id,
            role=ElectionRole.ORGANIZER
        )
    )

    db.session.add(election)
    db.session.commit()

    return jsonify({
        'id': election.id,
        'name': election.name,
        'description': election.description,
        'created_at': election.created_at.isoformat(),
        'created_by': election.created_by
    }), 201


# Get election by id
@election_bp.route('/<int:election_id>', methods=['GET'])
def get_election(election_id):
    """Get a specific election"""
    election = Election.query.get_or_404(election_id)
    return jsonify({
        'id': election.id,
        'name': election.name,
        'description': election.description,
        'created_at': election.created_at.isoformat(),
        'created_by': election.created_by
    })


@election_bp.route('/<int:election_id>/participants', methods=['GET'])
# @election_organizer_required
def get_election_participants(election_id):
    """Get all participants in an election with their roles"""
    participants = db.session.query(
        User,
        user_election_roles.c.role
    ).join(
        user_election_roles,
        (user_election_roles.c.user_id == User.id) &
        (user_election_roles.c.election_id == election_id)
    ).all()

    return jsonify([{
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': role.value if hasattr(role, 'value') else str(role)
    } for user, role in participants])


@election_bp.route('/<int:election_id>/participate', methods=['POST'])
@jwt_required()
def participate_in_election(election_id):
    """Mark the current user as participating in an election"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    role = data.get('role', 'voter')
    if role not in ['voter', 'candidate', 'organizer']:
        return jsonify({'message': 'Invalid role'}), 400

    # Check if the user is already participating in this election
    existing_participation = db.session.query(
        db.session.query(user_election_roles
                         ).filter(
            user_election_roles.c.user_id == user_id,
            user_election_roles.c.election_id == election_id
        ).exists()
    ).scalar()

    if not existing_participation:
        # Add the user as a voter to this election
        db.session.execute(
            user_election_roles.insert().values(
                user_id=user_id,
                election_id=election_id,
                role=ElectionRole.VOTER
            )
        )

        # Update participation metrics
        user.elections_participated += 1
        ParticipationService.handle_election_participation(user_id,
                                                           election_id, role)
        db.session.commit()
    else:
        return jsonify({'message': 
                        'User is already participating in this election'}), 400

    return jsonify({
        'message': f'Successfully joined the election as a {role}',
        'election_id': election_id,
        'role': role
    })


@election_bp.route('/<int:election_id>/register-candidate', methods=['POST'])
@jwt_required()
@candidate_eligible_required
@not_organizer_in_election
def register_as_candidate(election_id):
    """Register the current user as a candidate in an election"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)

    # Check if the election exists
    # election = Election.query.get_or_404(election_id)

    # Check if the user is already a candidate in this election
    existing_candidate_role = db.session.query(
        user_election_roles
    ).filter(
        user_election_roles.c.user_id == user_id,
        user_election_roles.c.election_id == election_id,
        user_election_roles.c.role == ElectionRole.CANDIDATE
    ).first()

    if existing_candidate_role:
        return jsonify({
            'message': 'User is already a candidate in this election'
        }), 400

    # Check if the user is already participating in this election
    existing_participation = db.session.query(
        user_election_roles
    ).filter(
        user_election_roles.c.user_id == user_id,
        user_election_roles.c.election_id == election_id
    ).first()

    if not existing_participation:
        # If not already participating, add as voter first
        db.session.execute(
            user_election_roles.insert().values(
                user_id=user_id,
                election_id=election_id,
                role=ElectionRole.VOTER
            )
        )
        user.elections_participated += 1

    # Update the role to candidate
    db.session.execute(
        user_election_roles.update()
        .where(
            (user_election_roles.c.user_id == user_id) &
            (user_election_roles.c.election_id == election_id)
        )
        .values(role=ElectionRole.CANDIDATE)
    )

    db.session.commit()

    return jsonify({
        'message': 'Successfully registered as candidate in election',
        'election_id': election_id
    })


@election_bp.route('/<int:election_id>/register-organizer', methods=['POST'])
@jwt_required()
@admin_required
@organizer_eligible_required
@not_candidate_in_election
def register_as_organizer(election_id):
    """Register a user as an organizer in an election - admin only"""
    # current_user_id = get_jwt_identity()
    # current_user = User.query.get_or_404(current_user_id)

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'message': 'User ID is required'}), 400

    user = User.query.get_or_404(user_id)

    # Check if the election exists
    # election = Election.query.get_or_404(election_id)

    # Check if the user is already an organizer in this election
    existing_organizer_role = db.session.query(
        user_election_roles
    ).filter(
        user_election_roles.c.user_id == user_id,
        user_election_roles.c.election_id == election_id,
        user_election_roles.c.role == ElectionRole.ORGANIZER
    ).first()

    if existing_organizer_role:
        return jsonify({
            'message': 'User is already an organizer in this election'
        }), 400

    # Check if the user is already participating in this election
    existing_participation = db.session.query(
        user_election_roles
    ).filter(
        user_election_roles.c.user_id == user_id,
        user_election_roles.c.election_id == election_id
    ).first()

    if not existing_participation:
        # If not already participating, add as voter first
        db.session.execute(
            user_election_roles.insert().values(
                user_id=user_id,
                election_id=election_id,
                role=ElectionRole.VOTER
            )
        )
        user.elections_participated += 1

    # Update the role to organizer
    db.session.execute(
        user_election_roles.update()
        .where(
            (user_election_roles.c.user_id == user_id) &
            (user_election_roles.c.election_id == election_id)
        )
        .values(role=ElectionRole.ORGANIZER)
    )

    db.session.commit()

    return jsonify({
        'message': 'Successfully registered user as organizer in election',
        'user_id': user_id,
        'election_id': election_id
    })


# Check if a user is participating at the election
@election_bp.route('/<int:election_id>/participation',
                   methods=['GET'])
@jwt_required()
def check_election_participation(election_id):
    """Check if the current user is participating in an election"""
    current_user_id = get_jwt_identity()

    # Check if the user has any role in this election
    is_participant = db.session.query(
        db.session.query(user_election_roles)
        .filter(
            user_election_roles.c.user_id == current_user_id,
            user_election_roles.c.election_id == election_id
        )
        .exists()
    ).scalar()

    # Get the user's role if they are participating
    user_role = None
    if is_participant:
        role = db.session.query(user_election_roles.c.role).filter(
            user_election_roles.c.user_id == current_user_id,
            user_election_roles.c.election_id == election_id
        ).scalar()

        user_role = role.value if role else str(role)

    return jsonify({
        'is_participant': is_participant,
        'role': user_role
    })


# Get all election of a user
@election_bp.route('/users/<int:user_id>/elections', methods=['GET'])
@jwt_required()
def get_elections_for_user(user_id):
    try:
        # Ensure the authenticated user is accessing their own elections
        current_user_id = int(get_jwt_identity())
        # Convert current_user_id to an integer if necessary
        if current_user_id != user_id:
            return jsonify({'message': 'Unauthorized access'}), 403

        # Fetch the user from the database
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Fetch elections where the user is a participant (voter, candidate,
        # or organizer)
        participant_elections = db.session.query(Election).join(
            user_election_roles,
            (user_election_roles.c.election_id == Election.id) &
            (user_election_roles.c.user_id == user_id)
        ).all()

        # Combine and deduplicate elections
        all_elections = list(set(participant_elections))

        return jsonify([{
            'id': election.id,
            'name': election.name,
            'description': election.description,
            'created_by': election.created_by,
            'created_at': election.created_at.isoformat()
            if election.created_at
            else None
        } for election in all_elections])
    except Exception as e:
        return jsonify({'message': str(e)}), 500


# Delete an election
@election_bp.route('/<int:election_id>', methods=['DELETE'])
def delete_election(election_id):
    election = Election.query.get_or_404(election_id)
    db.session.delete(election)
    db.session.commit()

    return jsonify({'result': True})


@election_bp.route('/elections/<int:election_id>', methods=['PUT'])
def update_election(election_id):
    data = request.get_json()
    election = Election.query.get_or_404(election_id)

    election.name = data.get('name', election.name)
    election.description = data.get('description', election.description)

    db.session.commit()
    return jsonify({'message': 'Election updated successfully'})
