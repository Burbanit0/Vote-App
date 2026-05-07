# tests/test_users.py


# ── Registration ───────────────────────────────────────────────────────────

def test_register(client, init_db):
    payload = {
        'username': 'newuser',
        'password': 'newpass',
        'first_name': 'New',
        'last_name': 'User',
        'role': 'User',
    }
    response = client.post('/api/auth/register', json=payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body['username'] == 'newuser'
    assert body['role'] == 'User'


def test_register_duplicate_username_returns_400(client, init_db):
    payload = {
        'username': 'testuserA',  # already seeded by init_db
        'password': 'anypass',
        'first_name': 'Dup',
        'last_name': 'User',
        'role': 'User',
    }
    response = client.post('/api/auth/register', json=payload)
    assert response.status_code == 400
    body = response.get_json()
    assert any(k in body for k in ('message', 'error'))


# ── Login ──────────────────────────────────────────────────────────────────

def test_login(client, init_db):
    payload = {'username': 'testuserA', 'password': 'testpass'}
    response = client.post('/api/auth/login', json=payload)
    assert response.status_code == 200
    body = response.get_json()
    assert 'access_token' in body
    assert body['username'] == 'testuserA'


def test_login_wrong_password_returns_401(client, init_db):
    payload = {'username': 'testuserA', 'password': 'wrongpass'}
    response = client.post('/api/auth/login', json=payload)
    assert response.status_code == 401


# ── Profile ────────────────────────────────────────────────────────────────

def test_get_profile(client, init_db, auth_header):
    response = client.get('/api/auth/profile', headers=auth_header)
    assert response.status_code == 200
    body = response.get_json()
    assert body['username'] == 'testuserA'
    assert 'is_admin' in body
    assert body['is_admin'] is False


def test_get_profile_without_token_returns_401(client, init_db):
    response = client.get('/api/auth/profile')
    assert response.status_code == 401


# ── Update user ────────────────────────────────────────────────────────────

def test_update_user(client, init_db, admin_auth_header):
    payload = {'first_name': 'Updated', 'last_name': 'Name'}
    response = client.put('/api/auth/1', json=payload, headers=admin_auth_header)
    assert response.status_code == 200
    body = response.get_json()
    assert body['first_name'] == 'Updated'
    assert body['last_name'] == 'Name'


def test_update_user_non_admin_returns_403(client, init_db, auth_header):
    # testuserA (role=User) tries to update a different user → admin_required blocks with 403
    payload = {'first_name': 'Hacker'}
    response = client.put('/api/auth/1', json=payload, headers=auth_header)
    assert response.status_code == 403


# ── User list ──────────────────────────────────────────────────────────────

def test_get_all_users(client, init_db, admin_auth_header):
    response = client.get('/api/auth/', headers=admin_auth_header)
    assert response.status_code == 200
    body = response.get_json()
    assert len(body) >= 2
    usernames = [u['username'] for u in body]
    assert 'adminA' in usernames
    assert 'testuserA' in usernames


def test_get_all_users_without_admin_returns_403(client, init_db, auth_header):
    # Non-admin authenticated user gets 403 from admin_required decorator
    response = client.get('/api/auth/', headers=auth_header)
    assert response.status_code == 403
