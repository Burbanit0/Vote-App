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
    assert body.get('error') == 'Username already exists'
    assert body.get('code') == 400


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


# ── Register voter ──────────────────────────────────────────────────────────

def test_register_voter(client, init_db):
    payload = {
        'username': 'voter1',
        'password': 'voterpass',
        'first_name': 'Voter',
        'last_name': 'One',
    }
    response = client.post('/api/auth/register/voter', json=payload)
    assert response.status_code == 201
    assert response.get_json()['message'] == 'User registered successfully'


def test_register_voter_missing_fields_returns_400(client, init_db):
    response = client.post('/api/auth/register/voter', json={'username': 'nopass'})
    assert response.status_code == 400
    assert 'error' in response.get_json()


def test_register_voter_duplicate_username_returns_400(client, init_db):
    payload = {'username': 'testuserA', 'password': 'anypass'}
    response = client.post('/api/auth/register/voter', json=payload)
    assert response.status_code == 400
    assert 'error' in response.get_json()


# ── Admin-only endpoint ─────────────────────────────────────────────────────

def test_admin_only_allows_admin(client, init_db, admin_auth_header):
    response = client.get('/api/auth/admin-only', headers=admin_auth_header)
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Welcome, Admin!'


def test_admin_only_denies_regular_user(client, init_db, auth_header):
    response = client.get('/api/auth/admin-only', headers=auth_header)
    assert response.status_code == 403


def test_admin_only_denies_unauthenticated(client, init_db):
    response = client.get('/api/auth/admin-only')
    assert response.status_code == 401


# ── Get single user ─────────────────────────────────────────────────────────

def test_get_user_by_id(client, init_db, auth_header):
    # testuserA is id=2 (adminA is id=1)
    response = client.get('/api/auth/2', headers=auth_header)
    assert response.status_code == 200
    body = response.get_json()
    assert body['username'] == 'testuserA'
    assert body['role'] == 'User'


def test_get_user_not_found_returns_404(client, init_db, auth_header):
    response = client.get('/api/auth/999', headers=auth_header)
    assert response.status_code == 404


def test_get_user_without_token_returns_401(client, init_db):
    response = client.get('/api/auth/2')
    assert response.status_code == 401


# ── Update user — additional paths ──────────────────────────────────────────

def test_update_user_password(client, init_db, admin_auth_header):
    payload = {'password': 'newpassword'}
    response = client.put('/api/auth/1', json=payload, headers=admin_auth_header)
    assert response.status_code == 200


def test_update_user_change_username(client, init_db, admin_auth_header):
    payload = {'username': 'newadmin'}
    response = client.put('/api/auth/1', json=payload, headers=admin_auth_header)
    assert response.status_code == 200
    assert response.get_json()['username'] == 'newadmin'


def test_update_user_duplicate_username_returns_400(client, init_db, admin_auth_header):
    payload = {'username': 'testuserA'}  # testuserA already exists
    response = client.put('/api/auth/1', json=payload, headers=admin_auth_header)
    assert response.status_code == 400
    assert 'error' in response.get_json()


def test_update_user_role_by_admin(client, init_db, admin_auth_header):
    payload = {'role': 'Admin'}
    response = client.put('/api/auth/2', json=payload, headers=admin_auth_header)
    assert response.status_code == 200
    assert response.get_json()['role'] == 'Admin'


def test_update_user_invalid_role_returns_400(client, init_db, admin_auth_header):
    payload = {'role': 'SuperAdmin'}
    response = client.put('/api/auth/2', json=payload, headers=admin_auth_header)
    assert response.status_code == 400
    assert 'error' in response.get_json()
