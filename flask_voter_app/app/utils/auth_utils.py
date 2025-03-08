# utils/auth_utils.py

from your_application import db
from your_application.models import User, Voter
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def register_user(username, password, role, first_name=None, last_name=None):
    new_user = User(username=username, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    if role == 'Voter':
        new_voter = Voter(user_id=new_user.id, first_name=first_name, last_name=last_name)
        db.session.add(new_voter)
        db.session.commit()

