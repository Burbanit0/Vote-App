import sys
import os
from unittest.mock import patch

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest # noqa
from app import create_app, db # noqa
from config import TestingConfig # noqa
from app.models import User, Election, Candidate, Voter # noqa


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


@pytest.fixture
def init_database(app):
    with app.app_context():
        # Create users
        user1 = User(username='user1', role='Voter')
        user1.set_password('password1')
        user2 = User(username='user2', role='Admin')
        user2.set_password('password2')

        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()
        user2_id = user2.id

        voter1 = Voter(first_name='John', last_name='Doe', user=user1)
        # Create candidates
        candidate1 = Candidate(first_name='Candidate1', last_name='One')
        candidate2 = Candidate(first_name='Candidate2', last_name='Two')

        db.session.add(candidate1)
        db.session.add(candidate2)
        db.session.add(voter1)
        db.session.commit()
        # Create elections
        election1 = Election(name='Election1', description='Description1',
                             created_by=user2_id)
        election1.candidates.append(candidate1)
        election1.voters.append(user2)

        election2 = Election(name='Election2', description='Description2',
                             created_by=user2_id)
        election2.candidates.append(candidate2)
        election2.voters.append(user1)

        db.session.add(election1)
        db.session.add(election2)
        db.session.commit()

    yield db


def test_create_election(client, init_database):
    # Login as an admin user to get the JWT token
    login_response = client.post(
        '/api/auth/login',
        json={'username': 'user2', 'password': 'password2'},
        headers={'Content-Type': 'application/json'}
    )
    assert login_response.status_code == 200
    access_token = login_response.get_json()['access_token']

    # Create an election
    response = client.post(
        '/elections/',
        json={'name': 'Election3',
              'description': 'Description3',
              'voters': [1],
              'candidates': [1]
              },
        headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
                }
    )
    print(response.get_json())
    assert response.status_code == 201
    assert 'election_id' in response.get_json()


def test_add_voter_to_election(client, init_database):
    # Login as a voter user to get the JWT token
    login_response = client.post(
        '/api/auth/login',
        json={'username': 'user1', 'password': 'password1'},
        headers={'Content-Type': 'application/json'}
    )
    assert login_response.status_code == 200
    access_token = login_response.get_json()['access_token']

    # Add voter to election
    response = client.post(
        '/elections/1/add_voter',
        headers={'Authorization': f'Bearer {access_token}',
                 'Content-Type': 'application/json'}
    )

    print(response.get_json())
    assert response.status_code == 200
    assert response.get_json()
    ['message'] == 'You have been added as a voter to the election.'


@patch('app.routes.elections.redis_client')
def test_get_elections(mock_redis, client, init_database):
    mock_redis.get.return_value = None
    response = client.get('/elections/')
    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_get_election_by_id(client, init_database):
    response = client.get('/elections/1')
    assert response.status_code == 200
    assert response.get_json()['name'] == 'Election1'


def test_get_candidates_for_election(client, init_database):
    response = client.get('/elections/elections/1/candidates')
    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_get_voters_for_election(client, init_database):
    response = client.get('/elections/elections/1/voters')
    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_get_elections_for_user(client, init_database):
    # Login as a voter user to get the JWT token
    login_response = client.post(
        '/api/auth/login',
        json={'username': 'user1', 'password': 'password1'},
        headers={'Content-Type': 'application/json'}
    )
    assert login_response.status_code == 200
    access_token = login_response.get_json()['access_token']

    # Get elections for user
    response = client.get(
        '/elections/users/1/elections',
        headers={'Authorization': f'Bearer {access_token}',
                 'Content-Type': 'application/json'}
    )

    print(response.get_json())
    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_delete_election(client, init_database):
    response = client.delete('/elections/1')
    assert response.status_code == 200
    assert response.get_json()['result'] is True


def test_update_election(client, init_database):
    response = client.put(
        '/elections/elections/1',
        json={'name': 'UpdatedElection1',
              'description': 'UpdatedDescription1'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Election updated successfully'
