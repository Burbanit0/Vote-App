import sys
import os
import json
from unittest.mock import patch

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest # noqa
from app import create_app, db # noqa
from config import TestingConfig # noqa
from app.models import User # noqa


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
            'role': 'User',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        assert response.status_code == 201
        assert json.loads(response.data) == {'message':
                                             'User registered successfully',
                                             'username': 'testuser',
                                             'user_id': 1,
                                             'role': 'User',
                                             'first_name': 'John',
                                             'last_name': 'Doe'}
