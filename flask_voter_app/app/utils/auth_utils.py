# utils/auth_utils.py
from app import db
from app.models import User, Voter
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()


def register_user(username, password, role, first_name, last_name):
    new_user = User(username=username, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    if role == 'Voter':
        new_voter = Voter(user_id=new_user.id, first_name=first_name,
                          last_name=last_name)
        db.session.add(new_voter)
        db.session.commit()
