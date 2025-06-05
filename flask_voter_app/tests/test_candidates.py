import sys
import os
import json
from unittest.mock import patch

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest # noqa
from app import create_app, db # noqa
from app.models import Candidate, Result # noqa
from config import TestingConfig # noqa


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


@patch('app.routes.candidates.redis_client')
def test_get_candidates(mock_redis, app, client):
    mock_redis.get.return_value = None
    with app.app_context():
        candidate = Candidate(first_name='John', last_name='Doe')
        db.session.add(candidate)
        db.session.commit()

    response = client.get('/candidates/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['first_name'] == 'John'
    assert data[0]['last_name'] == 'Doe'


@patch('app.routes.candidates.redis_client')
def test_create_candidate(mock_redis, app, client):
    response = client.post('/candidates/', json={'first_name': 'Jane',
                                                 'last_name': 'Doe'})
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['first_name'] == 'Jane'
    assert data['last_name'] == 'Doe'


def test_update_candidate(app, client):
    with app.app_context():
        candidate = Candidate(first_name='John', last_name='Doe')
        db.session.add(candidate)
        db.session.commit()
        candidate_id = candidate.id

    response = client.put(f'/candidates/{candidate_id}',
                          json={'first_name': 'Johnny'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['first_name'] == 'Johnny'
    assert data['last_name'] == 'Doe'


def test_delete_candidate(app, client):
    with app.app_context():
        candidate = Candidate(first_name='John', last_name='Doe')
        db.session.add(candidate)
        db.session.commit()
        candidate_id = candidate.id

    response = client.delete(f'/candidates/{candidate_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['result'] is True


@patch('app.routes.candidates.redis_client')
def test_get_candidate_results(mock_redis, app, client):
    with app.app_context():
        candidate = Candidate(first_name='John', last_name='Doe')
        db.session.add(candidate)
        db.session.commit()

        result = Result(candidate_id=candidate.id, vote_type='Primary',
                        vote_count=100)
        db.session.add(result)
        db.session.commit()
        candidate_id = candidate.id

    response = client.get(f'/candidates/{candidate_id}/results')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['candidate_name'] == 'John Doe'
    assert data[0]['vote_type'] == 'Primary'
    assert data[0]['vote_count'] == 100
