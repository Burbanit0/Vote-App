import os

from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.response_utils import error_response, success_response
from ..models import User
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..utils.decorators import admin_required
from ..services.user_service import UserService
from app import db
from app.extensions import sim_limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Rate limiter — shared instance, applied per-route
_AUTH_STORAGE = os.environ.get('REDIS_URL') or 'memory://'
_limiter = Limiter(key_func=get_remote_address, storage_uri=_AUTH_STORAGE)


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
@_limiter.limit("10 per hour")
def register_voter():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    first_name = data.get("first_name")
    last_name = data.get("last_name")

    return UserService.register(username, password, first_name, last_name, role="User")


@auth_bp.route("/login", methods=["POST"])
@_limiter.limit("20 per hour; 5 per minute")
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    result = UserService.login(username, password)
    return result


@auth_bp.route("/google", methods=["POST"])
def google_login():
    """Exchange a Google ID token for a Vote Lab JWT."""
    from flask import current_app
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    data = request.get_json()
    token = data.get("token")
    if not token:
        return error_response("Missing token", 400)

    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return error_response("Google login not configured", 501)

    try:
        info = google_id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
    except ValueError:
        return error_response("Invalid Google token", 401)

    google_sub = info.get("sub")
    email = info.get("email")
    first_name = info.get("given_name", "")
    last_name = info.get("family_name", "")

    user, _ = UserService.social_login_or_register(
        provider_id=google_sub, email=email,
        first_name=first_name, last_name=last_name,
        provider="google",
    )

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


@auth_bp.route("/github", methods=["GET"])
def github_redirect():
    """Redirect user to GitHub OAuth consent page."""
    from flask import current_app, redirect

    client_id = current_app.config.get("GITHUB_CLIENT_ID")
    if not client_id:
        return error_response("GitHub login not configured", 501)

    base_url = current_app.config.get("BASE_URL", "http://localhost:4433")
    redirect_uri = f"{base_url}/api/auth/github/callback"
    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user"
    )
    return redirect(github_url)


@auth_bp.route("/github/callback", methods=["GET"])
def github_callback():
    """Handle GitHub OAuth callback — exchange code for token, fetch user, login."""
    from flask import current_app, redirect as flask_redirect
    import requests as http_requests

    code = request.args.get("code")
    if not code:
        return error_response("Missing authorization code", 400)

    client_id = current_app.config.get("GITHUB_CLIENT_ID")
    client_secret = current_app.config.get("GITHUB_CLIENT_SECRET")
    base_url = current_app.config.get("BASE_URL", "http://localhost:4433")

    # Exchange code for access token
    token_resp = http_requests.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )
    token_data = token_resp.json()
    github_token = token_data.get("access_token")
    if not github_token:
        return error_response("Failed to exchange GitHub code for token", 400)

    # Fetch user info from GitHub API
    user_resp = http_requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {github_token}", "Accept": "application/json"},
    )
    github_user = user_resp.json()
    github_id = str(github_user.get("id"))
    email = github_user.get("email") or ""
    name = (github_user.get("name") or "").split(" ", 1)
    first_name = name[0] if name else ""
    last_name = name[1] if len(name) > 1 else ""

    # If no public email, fetch emails endpoint
    if not email:
        emails_resp = http_requests.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {github_token}", "Accept": "application/json"},
        )
        for e in emails_resp.json():
            if e.get("primary"):
                email = e.get("email", "")
                break

    user, _ = UserService.social_login_or_register(
        provider_id=github_id, email=email,
        first_name=first_name, last_name=last_name,
        provider="github",
    )

    from flask_jwt_extended import create_access_token
    access_token = create_access_token(identity=str(user.id))

    # Redirect back to frontend with token in URL
    frontend_url = "http://localhost:3000"
    return flask_redirect(f"{frontend_url}/oauth/callback?token={access_token}")


@auth_bp.route("/admin-only", methods=["GET"])
@admin_required
@jwt_required()
@sim_limiter.limit("30 per minute")
def admin_only():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if current_user.role != "Admin":
        return error_response("Access denied", 403)

    return success_response({"message": "Welcome, Admin!"}, 200)


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
@sim_limiter.limit("60 per minute")
def get_profile():
    current_user_id = int(get_jwt_identity())
    result = UserService.get_profile(current_user_id)
    return jsonify(result)


@auth_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
@admin_required
@sim_limiter.limit("30 per minute")
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
@sim_limiter.limit("30 per minute")
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
@sim_limiter.limit("60 per minute")
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
    })
