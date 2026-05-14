from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.auth_utils import register_user
from app.utils.response_utils import error_response, success_response
from ..models import User
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..utils.decorators import admin_required
from ..services.user_service import UserService
from app import db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Rate limiter — shared instance, applied per-route
_limiter = Limiter(key_func=get_remote_address)


@auth_bp.route("/register", methods=["POST"])
@_limiter.limit("10 per hour")
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    role = data.get("role", "User")

    return UserService.register(username, password, first_name, last_name, role)


@auth_bp.route("/register/voter", methods=["POST"])
def register_voter():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    first_name = data.get("first_name")
    last_name = data.get("last_name")

    if not username or not password:
        return error_response("Username and password are required", 400)

    if User.query.filter_by(username=username).first():
        return error_response("Username already exists", 400)

    register_user(username, password, "User", first_name, last_name)
    return success_response({"message": "User registered successfully"}, 201)


@auth_bp.route("/login", methods=["POST"])
@_limiter.limit("20 per hour; 5 per minute")
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    result = UserService.login(username, password)
    return result


@auth_bp.route("/admin-only", methods=["GET"])
@admin_required
@jwt_required()
def admin_only():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if current_user.role != "Admin":
        return error_response("Access denied", 403)

    return success_response({"message": "Welcome, Admin!"}, 200)


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    current_user_id = int(get_jwt_identity())
    result = UserService.get_profile(current_user_id)
    return jsonify(result)


@auth_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update_user(user_id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if current_user.role != "Admin" and current_user_id != user_id:
        return error_response("Unauthorized", 403)

    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if "username" in data:
        if (
            data["username"] != user.username
            and User.query.filter_by(username=data["username"]).first()
        ):
            return error_response("Username already exists", 400)
        user.username = data["username"]

    if "first_name" in data:
        user.first_name = data["first_name"]

    if "last_name" in data:
        user.last_name = data["last_name"]

    if "password" in data:
        user.set_password(data["password"])

    if current_user.role == "Admin" and "role" in data:
        if data["role"] not in ["User", "Admin"]:
            return error_response("Invalid role specified", 400)
        user.role = data["role"]

    db.session.commit()
    return jsonify({
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
    })


@auth_bp.route("/", methods=["GET"])
@jwt_required()
@admin_required
def get_all_users():
    users = User.query.all()
    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
        }
        for user in users
    ])


@auth_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
    })
