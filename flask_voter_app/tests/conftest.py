import pytest
from flask_jwt_extended import create_access_token
from datetime import datetime, timezone
from app import db, create_app
from app.models import User
from flask_bcrypt import generate_password_hash


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
            password_hash=generate_password_hash('adminpass').decode('utf-8'),
            role='Admin',
            first_name='Admin',
            last_name='User',
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(admin)

        user = User(
            username='testuserA',
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
