from flask import Blueprint, request, jsonify
import datetime
from flask_jwt_extended import get_jwt_identity, jwt_required
from app import db
from sqlalchemy.sql import func
from ..models import Election, User, ElectionRole, Vote, user_election_roles
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
    """Get filtered and sorted elections with organizer details"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '', type=str)
    sort_by = request.args.get('sort_by', 'name', type=str)
    sort_dir = request.args.get('sort_dir', 'asc', type=str)

    # Base query with join
    query = db.session.query(
        Election,
        User.first_name,
        User.last_name
    ).join(
        User, Election.created_by == User.id
    )

    # Apply search filter if provided
    if search:
        query = query.filter(
            (Election.name.ilike(f'%{search}%')) |
            (Election.description.ilike(f'%{search}%'))
        )

    # Apply sorting
    if sort_by == 'name':
        if sort_dir == 'desc':
            query = query.order_by(Election.name.desc())
        else:
            query = query.order_by(Election.name.asc())
    elif sort_by == 'date':
        if sort_dir == 'desc':
            query = query.order_by(Election.start_date.desc())
        else:
            query = query.order_by(Election.start_date.asc())

    # Paginate the results
    paginated_elections = query.paginate(page=page, per_page=per_page,
                                         error_out=False)

    # Format the results
    formatted_elections = [{
        'id': election.id,
        'name': election.name,
        'description': election.description,
        'start_date': election.start_date.isoformat()
        if election.start_date else None,
        'end_date': election.end_date.isoformat()
        if election.end_date else None,
        'created_at': election.created_at,
        'created_by': {
            'id': election.created_by,
            'first_name': first_name,
            'last_name': last_name
        },
    } for election, first_name, last_name in paginated_elections.items]

    return jsonify({
        'elections': formatted_elections,
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
    election = db.session.query(
        Election,
        User.first_name,
        User.last_name
    ).join(
        User, Election.created_by == User.id
    ).filter(
        Election.id == election_id
    ).first_or_404(description='Election not found')

    formatted_election = {
        'id': election[0].id,
        'name': election[0].name,
        'description': election[0].description,
        'start_date': election[0].start_date.isoformat()
        if election[0].start_date else None,
        'end_date': election[0].end_date.isoformat()
        if election[0].end_date else None,
        'created_at': election[0].created_at,
        'created_by': {
            'id': election[0].created_by,
            'first_name': election[1],
            'last_name': election[2]
        },
    }

    return jsonify(formatted_election)


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


@election_bp.route('/<int:election_id>/cancel-participation', methods=['POST'])
@jwt_required()
def cancel_participation(election_id):
    """Cancel participation in an election"""
    current_user_id = get_jwt_identity()

    # Check if election has started
    election = Election.query.get(election_id)
    if not election or election.start_date <= datetime.utcnow():
        return jsonify({'message':
                        'Cannot cancel participation after '
                        'election has started'}), 400

    # Remove user from election
    db.session.execute(
        user_election_roles.delete().where(
            user_election_roles.c.user_id == current_user_id,
            user_election_roles.c.election_id == election_id
        )
    )

    db.session.commit()

    return jsonify({
        'message': 'Successfully canceled participation in election',
        'election_id': election_id
    })


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


@election_bp.route('/<int:election_id>/results', methods=['GET'])
@jwt_required()
def get_election_results(election_id):
    """Get results for an election"""
    election = Election.query.get_or_404(election_id)

    # Check if election has ended
    if election.end_date > datetime.utcnow():
        return jsonify({'message': 'Election has not ended yet'}), 400

    # Get all voting methods used in this election
    voting_methods = db.session.query(Vote.vote_type).filter(
        Vote.election_id == election_id
    ).distinct().all()

    results = {}

    # Get overall results
    overall_results = db.session.query(
        User.username,
        func.count(Vote.id).label('vote_count')
    ).join(
        Vote, Vote.candidate_id == User.id
    ).filter(
        Vote.election_id == election_id
    ).group_by(
        User.username
    ).order_by(
        func.count(Vote.id).desc()
    ).all()

    results['overall'] = [{
        'candidate': candidate,
        'votes': votes
    } for candidate, votes in overall_results]

    # Get results by voting method
    for method in voting_methods:
        method_results = db.session.query(
            User.username,
            func.count(Vote.id).label('vote_count')
        ).join(
            Vote, Vote.candidate_id == User.id
        ).filter(
            Vote.election_id == election_id,
            Vote.vote_type == method[0]
        ).group_by(
            User.username
        ).order_by(
            func.count(Vote.id).desc()
        ).all()

        results[method[0]] = [{
            'candidate': candidate,
            'votes': votes
        } for candidate, votes in method_results]

    # Get total votes
    total_votes = db.session.query(func.count(Vote.id)).filter(
        Vote.election_id == election_id
    ).scalar()

    return jsonify({
        'election_id': election_id,
        'election_name': election.name,
        'results': results,
        'total_votes': total_votes,
        'voting_method': election.voting_method,
        'start_date': election.start_date.isoformat(),
        'end_date': election.end_date.isoformat()
    })
