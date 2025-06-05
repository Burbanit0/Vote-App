import sys
import os
import json
from unittest.mock import patch

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest # noqa
from app import create_app, db # noqa
from config import TestingConfig # noqa
from app.models import User, Voter # noqa


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_register_user(app, client):
    with patch('app.utils.auth_utils.register_user') as mock_register_user:
        mock_register_user.return_value = None
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'testpass',
            'role': 'Voter',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        assert response.status_code == 201
        assert json.loads(response.data) == {'message':
                                             'User registered successfully'}


def test_login_user(app, client):
    # Create a test user with a hashed password
    with app.app_context():
        user = User(username='testuser', role='Voter')
        user.set_password('testpass')
        db.session.add(user)
        voter = Voter(first_name='Jane', last_name='Doe', user=user)
        db.session.add(voter)
        db.session.commit()
        voter_id = voter.id

    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data
    assert data['role'] == 'Voter'
    assert 'voter' in data
    assert data['voter']['first_name'] == 'Jane'
    assert data['voter']['last_name'] == 'Doe'
    assert data['voter']['id'] == voter_id


def test_admin_only_access_granted(app, client):
    # Create an admin user
    with app.app_context():
        admin_user = User(username='adminuser', role='Admin')
        admin_user.set_password('adminpass')
        db.session.add(admin_user)
        db.session.commit()

    # Log in as the admin user to get the JWT token
    login_response = client.post(
        '/api/auth/login',
        data=json.dumps({'username': 'adminuser', 'password': 'adminpass'}),
        content_type='application/json'
    )

    assert login_response.status_code == 200
    login_data = json.loads(login_response.data)
    assert 'access_token' in login_data
    assert 'role' in login_data
    assert login_data['role'] == 'Admin'
    access_token = login_data['access_token']

    # Make a request to the admin-only endpoint with the token
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = client.get('/api/auth/admin-only', headers=headers)

    # Verify that access is granted
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data == {"message": "Welcome, Admin!"}


def test_admin_only_access_denied(app, client):
    # Create a non-admin user
    with app.app_context():
        non_admin_user = User(username='nonadminuser', role='Voter')
        non_admin_user.set_password('votepass')
        db.session.add(non_admin_user)
        db.session.commit()

        non_admin_user_id = non_admin_user.id
        voter = Voter(first_name='Jane', last_name='Doe',
                      user_id=non_admin_user_id)
        db.session.add(voter)
        db.session.commit()

    # Log in as the non-admin user to get the JWT token
    login_response = client.post('/api/auth/login', json={
        'username': 'nonadminuser',
        'password': 'votepass'
    }, headers={'Content-Type': 'application/json'})

    assert login_response.status_code == 200
    login_data = json.loads(login_response.data)
    assert 'access_token' in login_data
    access_token = login_data['access_token']

    # Make a request to the admin-only endpoint with the token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = client.get('/api/auth/admin-only', headers=headers)

    # Verify that access is denied
    assert response.status_code == 403
    assert json.loads(response.data) == {"message": "Access denied"}


def test_get_profile(app, client):
    # Create a test user with a voter and get an access token
    with app.app_context():
        user = User(username='testuser', role='Voter')
        user.set_password('testpass')
        db.session.add(user)
        voter = Voter(first_name='John', last_name='Doe', user=user)
        db.session.add(voter)
        db.session.commit()

    login_response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass'
    })
    access_token = json.loads(login_response.data)['access_token']

    # Access the profile route with the access token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = client.get('/api/auth/profile', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['username'] == 'testuser'
    assert data['voter']['first_name'] == 'John'
    assert data['voter']['last_name'] == 'Doe'


def test_get_current_voter(app, client):
    # Create a test user with a voter and get an access token
    with app.app_context():
        user = User(username='testuser', role='Voter')
        user.set_password('testpass')
        voter = Voter(first_name='John', last_name='Doe', user=user)
        db.session.add(user)
        db.session.add(voter)
        db.session.commit()

    login_response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass'
    })
    access_token = json.loads(login_response.data)['access_token']

    # Access the current_voter route with the access token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = client.get('/api/auth/current_voter', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['first_name'] == 'John'
    assert data['last_name'] == 'Doe'


def test_get_users(app, client):
    # Create a test user
    with app.app_context():
        user = User(username='testuser', role='Voter')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

    response = client.get('/api/auth/')
    assert response.status_code == 200
    assert len(json.loads(response.data)) == 1
