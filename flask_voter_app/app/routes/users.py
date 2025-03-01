from flask import Blueprint, request, jsonify
from ..models import User, db
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    if not username or not password or role not in ['Voter', 'Admin']:
        return jsonify({"message": "Invalid input"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400

    new_user = User(username=username, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity={"id": user.id, "role": user.role})
    return jsonify(access_token=access_token, role=user.role), 200

@auth_bp.route('/admin-only', methods=['GET'])
@jwt_required()
def admin_only():
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'Admin':
        return jsonify({"message": "Access denied"}), 403

    # Admin-only logic here
    return jsonify({"message": "Welcome, Admin!"}), 200
