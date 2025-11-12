# tests/test_users.py

def test_register(client, init_db):
    data = {
        'username': 'newuser',
        'password': 'newpass',
        'first_name': 'New',
        'last_name': 'User',
        'role': 'User'
    }
    response = client.post('/api/auth/register', json=data)
    assert response.status_code == 200
    data = response.get_json()
    assert data[0]['username'] == 'newuser'
    assert data[0]['role'] == 'User'


def test_login(client, init_db):
    data = {
        'username': 'testuserA',
        'password': 'testpass'
    }
    response = client.post('/api/auth/login', json=data)
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data[0]
    assert data[0]['username'] == 'testuserA'


def test_get_profile(client, init_db, auth_header):
    response = client.get('/api/auth/profile', headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['username'] == 'testuserA'
    assert 'participation_details' in data


def test_update_user(client, init_db, admin_auth_header):
    data = {
        'first_name': 'Updated',
        'last_name': 'Name'
    }
    response = client.put('/api/auth/1', json=data, headers=admin_auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['first_name'] == 'Updated'
    assert data['last_name'] == 'Name'


def test_get_all_users(client, init_db, admin_auth_header):
    response = client.get('/api/auth/', headers=admin_auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 1
    assert data[0]['username'] == 'adminA' or data[0]['username'] == 'testuserA'
