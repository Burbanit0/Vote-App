import sys
from unittest.mock import MagicMock

import pytest
from flask_jwt_extended import create_access_token
from datetime import datetime, timezone
from app import db, create_app
from app.models import User
from flask_bcrypt import generate_password_hash

# ── Graceful flask_limiter handling ──────────────────────────────────────────
# If flask_limiter is not installed, mock the module so that
# app/routes/users.py can still be imported without ImportError.
try:
    from flask_limiter import Limiter  # noqa: F401
    HAS_LIMITER = True
except ImportError:
    HAS_LIMITER = False

    mock_limiter_util = MagicMock()
    mock_limiter_util.get_remote_address = MagicMock(return_value='127.0.0.1')

    mock_limiter_mod = MagicMock()
    mock_limiter_mod.Limiter = MagicMock(
        return_value=MagicMock(limit=lambda x: lambda f: f)
    )
    mock_limiter_mod.util = mock_limiter_util

    sys.modules['flask_limiter'] = mock_limiter_mod
    sys.modules['flask_limiter.util'] = mock_limiter_util


@pytest.fixture(scope='function')
def app():
    app = create_app(config_object="config.TestingConfig")
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture(scope='function')
def db_session(app):
    with app.app_context():
        yield db.session


@pytest.fixture(scope='function')
def init_db(app):
    with app.app_context():
        db.session.begin()

        admin = User(
            username='adminA',
            email='adminA@vote-app.local',
            password_hash=generate_password_hash('adminpass').decode('utf-8'),
            role='Admin',
            is_superuser=True,
            first_name='Admin',
            last_name='User',
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(admin)

        user = User(
            username='testuserA',
            email='testuserA@vote-app.local',
            password_hash=generate_password_hash('testpass').decode('utf-8'),
            role='User',
            first_name='Test',
            last_name='User',
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(user)
        db.session.commit()
        yield db
        db.session.rollback()
        db.session.remove()


@pytest.fixture
def auth_header(client, app):
    with app.app_context():
        user = User.query.filter_by(username='testuserA').first()
        access_token = create_access_token(identity=str(user.id))
        return {'Authorization': f'Bearer {access_token}'}


@pytest.fixture
def admin_auth_header(client, app):
    with app.app_context():
        user = User.query.filter_by(username='adminA').first()
        access_token = create_access_token(identity=str(user.id))
        return {'Authorization': f'Bearer {access_token}'}
