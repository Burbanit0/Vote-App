from flask import jsonify
from app.models import User
from app.utils.auth_utils import register_user


class UserService:
    @staticmethod
    def register(username, password, first_name, last_name, role="User"):
        if not username or not password:
            return {"error": "Missing required fields"}, 400

        if role not in ["User", "Admin"]:
            return {"message": "Invalid role specified"}, 400

        if User.query.filter_by(username=username).first():
            return {"message": "Username already exists"}, 400

        try:
            register_user(username, password, role, first_name, last_name)
            user = User.query.filter_by(username=username).first()
            return {
                "message": "User registered successfully",
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }, 201
        except Exception as e:
            return {"error": str(e)}, 500

    @staticmethod
    def login(username, password):
        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 401

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({"message": "Invalid credentials"}), 401

        from flask_jwt_extended import create_access_token

        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "access_token": access_token,
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }), 200

    @staticmethod
    def get_profile(user_id):
        user = User.query.get_or_404(user_id)
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "party_id": user.party_id,
            "is_admin": user.role == "Admin",
        }
