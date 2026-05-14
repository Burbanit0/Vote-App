from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models import User
from app.utils.response_utils import error_response


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or user.role != "Admin":
            return error_response("Admin access required", 403)

        return fn(*args, **kwargs)

    return wrapper
