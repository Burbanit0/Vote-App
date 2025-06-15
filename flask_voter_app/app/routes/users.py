from flask import Blueprint, request, jsonify
from app.utils.auth_utils import register_user
from ..models import User
from flask_jwt_extended import create_access_token, get_jwt_identity, \
    jwt_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    # Validate input data
    if not username or not password or not role:
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        register_user(username, password, role, first_name, last_name)
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id,
                                       additional_claims={"role": user.role})
    if (user.role == 'Admin'):
        return jsonify(access_token=access_token, role=user.role)
    else:
        voter_data = {'id': user.voter.id,
                      'user_id': user.voter.user_id,
                      'first_name': user.voter.first_name,
                      'last_name': user.voter.last_name}
        return jsonify(access_token=access_token, role=user.role,
                       voter=voter_data), 200


@auth_bp.route('/admin-only', methods=['GET'])
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

    current_user = User.query.get(current_user_id)

    if not current_user:
        return jsonify({"msg": "User not found"}), 404

    # Prepare the user data to be sent as JSON
    user_data = {
        'id': current_user.id,
        'username': current_user.username,
        'role': current_user.role,
        'created_at': current_user.created_at.isoformat()
    }

    # Include voter information if available
    if current_user.voter:
        user_data['voter'] = {
            'first_name': current_user.voter.first_name,
            'last_name': current_user.voter.last_name
        }

    return jsonify(user_data)


@auth_bp.route('/current_voter', methods=['GET'])
@jwt_required()
def get_current_profile():
    # Retrieve the logged-in user's information using the primary key
    current_user_identity = get_jwt_identity()

    # Convert current_user_id to an integer if necessary
    current_user_id = int(current_user_identity)

    current_user = User.query.get(current_user_id)

    if not current_user:
        return jsonify({"msg": "User not found"}), 404
    # Include voter information if available
    if current_user.voter:
        current_voter = {
            'first_name': current_user.voter.first_name,
            'last_name': current_user.voter.last_name
        }

    return jsonify(current_voter)


@auth_bp.route('/', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
    } for user in users])
