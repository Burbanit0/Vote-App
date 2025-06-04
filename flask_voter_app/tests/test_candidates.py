import sys
import os
import json
from unittest.mock import patch
import pytest
from flask import Flask
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import db # noqa
from app.models import Candidate, Result # noqa
from app.routes.candidates import bp as candidates_bp # noqa


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(candidates_bp)

    yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@patch('app.candidates.redis_client')
def test_get_candidates(mock_redis, client):
    mock_redis.get.return_value = None
    candidate = Candidate(first_name='John', last_name='Doe')
    db.session.add(candidate)
    db.session.commit()

    response = client.get('/candidates/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['first_name'] == 'John'
    assert data[0]['last_name'] == 'Doe'


@patch('app.candidates.redis_client')
def test_create_candidate(mock_redis, client):
    response = client.post('/candidates/', json={'first_name': 'Jane',
                                                 'last_name': 'Doe'})
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['first_name'] == 'Jane'
    assert data['last_name'] == 'Doe'


def test_update_candidate(client):
    candidate = Candidate(first_name='John', last_name='Doe')
    db.session.add(candidate)
    db.session.commit()

    response = client.put(f'/candidates/{candidate.id}', json={
        'first_name': 'Johnny'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['first_name'] == 'Johnny'
    assert data['last_name'] == 'Doe'


def test_delete_candidate(client):
    candidate = Candidate(first_name='John', last_name='Doe')
    db.session.add(candidate)
    db.session.commit()

    response = client.delete(f'/candidates/{candidate.id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['result'] is True


@patch('app.candidates.redis_client')
def test_get_candidate_results(mock_redis, client):
    candidate = Candidate(first_name='John', last_name='Doe')
    db.session.add(candidate)
    db.session.commit()

    result = Result(candidate_id=candidate.id, vote_type='Primary',
                    vote_count=100)
    db.session.add(result)
    db.session.commit()

    response = client.get(f'/candidates/{candidate.id}/results')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['candidate_name'] == 'John Doe'
    assert data[0]['vote_type'] == 'Primary'
    assert data[0]['vote_count'] == 100
