# utils/auth_utils.py
from app import db
from app.models import User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()


def register_user(username, password, role, first_name, last_name):
    new_user = User(username=username,
                    first_name=first_name,
                    role=role,
                    last_name=last_name,
                    elections_participated=0,
                    elections_voted_in=0
                    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
