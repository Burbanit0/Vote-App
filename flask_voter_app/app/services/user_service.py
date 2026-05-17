import random

from app import db
from app.models import User
from app.utils.auth_utils import register_user
from app.utils.response_utils import error_response, success_response


class UserService:
    @staticmethod
    def _validate_password_strength(password: str) -> str | None:
        if len(password) < 8:
            return "Password must be at least 8 characters long"
        return None

    @staticmethod
    def register(username, password, first_name, last_name, role="User"):
        if not username or not password:
            return error_response("Missing required fields", 400)

        pw_error = UserService._validate_password_strength(password)
        if pw_error:
            return error_response(pw_error, 400)

        if role not in ["User", "Admin"]:
            return error_response("Invalid role specified", 400)

        if User.query.filter_by(username=username).first():
            return error_response("Username already exists", 400)

        try:
            register_user(username, password, role, first_name, last_name)
            user = User.query.filter_by(username=username).first()
            return success_response({
                "message": "User registered successfully",
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }, 201)
        except Exception as e:
            return error_response(str(e), 500)

    @staticmethod
    def login(username, password):
        if not username or not password:
            return error_response("Username and password are required", 401)

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return error_response("Invalid credentials", 401)

        from flask_jwt_extended import create_access_token

        access_token = create_access_token(identity=str(user.id))
        return success_response({
            "access_token": access_token,
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }, 200)

    @staticmethod
    def get_profile(user_id):
        user = User.query.get_or_404(user_id)
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_admin": user.role == "Admin",
        }

    @staticmethod
    def social_login_or_register(provider_id, email=None, first_name=None, last_name=None, provider='google'):
        """Find or create a user via social login. Returns (user, is_new)."""
        id_field = f"{provider}_id"

        # 1. Lookup by provider ID
        user = User.query.filter_by(**{id_field: provider_id}).first()
        if user:
            return user, False

        # 2. Lookup by email and link the provider ID
        if email:
            user = User.query.filter_by(email=email).first()
            if user:
                setattr(user, id_field, provider_id)
                db.session.commit()
                return user, False

        # 3. Create new user
        base_username = email.split('@')[0] if email else f'user{provider_id[:8]}'
        username = base_username
        while User.query.filter_by(username=username).first():
            username = f"{base_username}_{random.randint(1000, 9999)}"

        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='User',
            password_hash='*',
            **{id_field: provider_id}
        )
        db.session.add(new_user)
        db.session.commit()
        return new_user, True
