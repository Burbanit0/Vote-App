import sys
import os
import json
import pytest

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db # noqa
from config import TestingConfig # noqa
from app.models import Voter, Vote, Candidate, User # noqa


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


def test_get_voters(app, client):
    with app.app_context():
        voter = Voter(first_name='John', last_name='Doe', user_id=1)
        db.session.add(voter)
        db.session.commit()

    response = client.get('/voters/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['first_name'] == 'John'
    assert data[0]['last_name'] == 'Doe'


def test_create_voter(app, client):
    with app.app_context():
        user = User(id=1, username='testuser', password_hash='testuser',
                    role='Voter')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    response = client.post('/voters/', json={'user_id': user_id,
                                             'first_name': 'Jane',
                                             'last_name': 'Doe'})
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['first_name'] == 'Jane'
    assert data['last_name'] == 'Doe'
    assert data['user_id'] == user_id


def test_update_voter(app, client):
    with app.app_context():
        voter = Voter(first_name='John', last_name='Doe', user_id=1)
        db.session.add(voter)
        db.session.commit()
        voter_id = voter.id

    response = client.put(f'/voters/{voter_id}', json={'first_name': 'Johnny'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['first_name'] == 'Johnny'
    assert data['last_name'] == 'Doe'


def test_delete_voter(app, client):
    with app.app_context():
        voter = Voter(first_name='John', last_name='Doe', user_id=1)
        db.session.add(voter)
        db.session.commit()
        voter_id = voter.id

    response = client.delete(f'/voters/{voter_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['result'] is True


def test_get_voter_votes(app, client):
    with app.app_context():
        voter = Voter(first_name='John', last_name='Doe', user_id=1)
        candidate = Candidate(first_name='Candidate', last_name='One')
        db.session.add(voter)
        db.session.add(candidate)
        db.session.commit()
        voter_id = voter.id
        candidate_id = candidate.id

        vote = Vote()
        vote.voter_id = voter_id
        vote.candidate_id = candidate_id
        vote.vote_type = 'single'
        db.session.add(vote)
        db.session.commit()

    response = client.get(f'/voters/{voter_id}/votes')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['candidate_name'] == 'Candidate One'
    assert data[0]['vote_type'] == 'single'


def test_get_voters_with_single_choice(app, client):
    with app.app_context():
        voter = Voter(first_name='John', last_name='Doe', user_id=1)
        candidate = Candidate(first_name='Candidate', last_name='One')
        db.session.add(voter)
        db.session.add(candidate)
        db.session.commit()
        voter_id = voter.id
        candidate_id = candidate.id

        vote = Vote()
        vote.voter_id = voter_id
        vote.candidate_id = candidate_id
        vote.vote_type = 'single'
        db.session.add(vote)
        db.session.commit()

    response = client.get('/voters/single-choice')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['voter_first_name'] == 'John'
    assert data[0]['choice'] == candidate_id

# Add similar tests for other endpoints like multiple-choices, ranked,
# weighted, and rate
