# utils/auth_utils.py
from app import db
from app.models import User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()


def register_user(username, password, role, first_name, last_name, email=None):
    # Phase 4.3.a: email is now a NOT NULL UNIQUE column required by
    # fastapi-users. Legacy register form doesn't pass it yet, so we
    # synthesise <username>@vote-app.local until Phase 4.3.b ships the
    # email-first registration flow.
    new_user = User(
        username=username,
        email=email or f"{username}@vote-app.local",
        first_name=first_name,
        role=role,
        is_superuser=(role == "Admin"),
        last_name=last_name,
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
