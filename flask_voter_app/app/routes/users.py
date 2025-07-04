from flask import Blueprint, request, jsonify
from app.utils.auth_utils import register_user
from ..models import User, ElectionRole, Vote, \
    get_elections_user_has_voted_in, user_election_roles
from flask_jwt_extended import create_access_token, get_jwt_identity, \
    jwt_required
from ..utils.decorators import admin_required
from app import db

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    role = data.get('role', 'User')

    # Validate input data
    if not username or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    if role not in ['User', 'Admin']:
        return jsonify({'message': 'Invalid role specified'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400
    try:
        register_user(username, password, role, first_name, last_name)

        user = User.query.filter_by(username=username).first()

        return jsonify({
            'message': 'User registered successfully',
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'first_name': user.first_name,
            'last_name': user.last_name
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/register/voter', methods=['POST'])
def register_voter():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400

    # Voter registration always creates a User with role 'User'
    register_user(username, password, first_name, last_name, role='User')

    return jsonify({
        'message': 'User registered successfully'
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'access_token': access_token,
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'first_name': user.first_name,
        'last_name': user.last_name
    }), 200


@auth_bp.route('/admin-only', methods=['GET'])
@admin_required
@jwt_required()
def admin_only():
    current_user_id = get_jwt_identity()  # This returns just the user ID
    # Use the user ID to get the user
    current_user = User.query.get(current_user_id)
    # Optionally, you can access additional claims like the role
    # current_user_role = get_jwt()["role"]

    if current_user.role != 'Admin':
        return jsonify({"message": "Access denied"}), 403

    # Admin-only logic here
    return jsonify({"message": "Welcome, Admin!"}), 200


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    # Retrieve the logged-in user's information using the primary key
    current_user_identity = get_jwt_identity()

    # Convert current_user_id to an integer if necessary
    current_user_id = int(current_user_identity)

    current_user = User.query.get_or_404(current_user_id)

    # Get participation details
    participation = db.session.query(
        user_election_roles.c.election_id,
        user_election_roles.c.role
    ).filter(
        user_election_roles.c.user_id == current_user_id
    ).all()

    participation_details = {
        'voter': [],
        'candidate': [],
        'organizer': []
    }

    for election_id, role in participation:
        participation_details[role.value].append(election_id)

    # Get elections where user has voted
    voted_elections = db.session.query(
        Vote.election_id
    ).filter(
        Vote.voter_id == current_user_id
    ).distinct().all()

    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'role': current_user.role,
        'is_admin': current_user.role == 'Admin',
        'elections_participated': current_user.elections_participated,
        'elections_voted_in': current_user.elections_voted_in,
        'participation_details': participation_details,
        'voted_in_elections':
        [election_id for (election_id,) in voted_elections]
    })


@auth_bp.route('/participation', methods=['GET'])
@jwt_required()
def get_participation_requirements():
    """Get participation requirements and current status"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)

    # Get elections where user is a candidate
    candidate_elections = db.session.query(
        user_election_roles.c.election_id
    ).filter(
        user_election_roles.c.user_id == user_id,
        user_election_roles.c.role == ElectionRole.CANDIDATE
    ).count()

    # Get elections where user is an organizer
    organizer_elections = db.session.query(
        user_election_roles.c.election_id
    ).filter(
        user_election_roles.c.user_id == user_id,
        user_election_roles.c.role == ElectionRole.ORGANIZER
    ).count()

    # Get elections where user has voted
    voted_elections_count = db.session.query(
        Vote.election_id
    ).filter(
        Vote.voter_id == user_id
    ).distinct().count()

    return jsonify({
        'current_participation': user.elections_participated,
        'current_votes_cast': voted_elections_count,
        'candidate_requirements': {
            'minimum_elections_participated': 10,
            'current_elections_as_candidate': candidate_elections,
            'eligible_for_candidate': user.elections_participated >= 10
        },
        'organizer_requirements': {
            'minimum_elections_participated': 15,
            'minimum_elections_voted_in': 5,
            'current_elections_as_organizer': organizer_elections,
            'eligible_for_organizer': user.elections_participated >= 15
            and voted_elections_count >= 5
        }
    })


@auth_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_user(user_id):
    """Update a user - admin only endpoint"""
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    # Admins can update any user, regular users can only update themselves
    if current_user.role != 'Admin' and current_user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403

    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if 'username' in data:
        if data['username'] != user.username and User.query.filter_by(
                        username=data['username']).first():
            return jsonify({'message': 'Username already exists'}), 400
        user.username = data['username']

    if 'first_name' in data:
        user.first_name = data['first_name']

    if 'last_name' in data:
        user.last_name = data['last_name']

    if 'password' in data:
        user.password_hash = User.set_password(data['password'])

    # Only admins can change roles
    if current_user.role == 'Admin' and 'role' in data:
        if data['role'] not in ['User', 'Admin']:
            return jsonify({'message': 'Invalid role specified'}), 400
        user.role = data['role']

    db.session.commit()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role
    })


@auth_bp.route('/', methods=['GET'])
@jwt_required()
@admin_required
def get_all_users():
    """Get all users - admin only endpoint"""
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'elections_participated': user.elections_participated,
        'elections_voted_in': user.elections_voted_in
    } for user in users])


@auth_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Get a specific user"""
    # current_user_id = get_jwt_identity()

    user = User.query.get_or_404(user_id)

    # # Admins can view any user, regular users can only view themselves
    # if current_user.role != 'Admin' and current_user_id != user_id:
    #     return jsonify({'message': 'Unauthorized'}), 403

    # Get participation details
    participation = db.session.query(
        user_election_roles.c.election_id,
        user_election_roles.c.role
    ).filter(
        user_election_roles.c.user_id == user_id
    ).all()

    participation_details = {
        'voter': [],
        'candidate': [],
        'organizer': []
    }

    for election_id, role in participation:
        participation_details[role.value].append(election_id)

    return jsonify({
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'elections_participated': user.elections_participated,
        'elections_voted_in': user.elections_voted_in,
        'participation_details': participation_details
    })


@auth_bp.route('/users/me/permissions', methods=['GET'])
@jwt_required()
def get_user_permissions():
    """Get the current user's permissions"""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)

    # Calculate if user can create elections
    can_create_elections = (
        user.role == 'Admin' or
        user.participation_points >= 100
    )

    return jsonify({
        'is_admin': user.role == 'Admin',
        'participation_points': user.participation_points,
        'can_create_elections': can_create_elections
    })


@auth_bp.route('/users/me/participation', methods=['GET'])
@jwt_required()
def get_participation_data():
    """Get the current user's participation data"""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)

    # Determine level based on points
    if user.participation_points >= 1000:
        level = 'Legend'
        next_level = 1000
    elif user.participation_points >= 500:
        level = 'Master'
        next_level = 1000
    elif user.participation_points >= 200:
        level = 'Expert'
        next_level = 500
    elif user.participation_points >= 50:
        level = 'Active'
        next_level = 200
    else:
        level = 'Beginner'
        next_level = 50

    return jsonify({
        'points': user.participation_points,
        'level': level,
        'nextLevel': next_level
    })


@auth_bp.route('/users/me/voted-elections', methods=['GET'])
@jwt_required()
def get_voted_elections():
    """Get elections that the current user has voted in"""
    current_user_id = get_jwt_identity()

    elections = get_elections_user_has_voted_in(current_user_id)

    return jsonify([{
        'id': election.id,
        'name': election.name,
        'description': election.description,
        'start_date': election.start_date.isoformat()
        if election.start_date else None,
        'end_date': election.end_date.isoformat()
        if election.end_date else None
    } for election in elections])
