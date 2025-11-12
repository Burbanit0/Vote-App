# tests/test_parties.py
from app.models import Party, User


def test_get_all_parties_empty(client, init_db):
    response = client.get('/parties/')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 0


def test_create_party(client, init_db, auth_header):
    data = {
        'name': 'Test Party',
        'description': 'A test party'
    }
    response = client.post('/parties/', json=data, headers=auth_header)
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Test Party'
    assert 'id' in data


def test_get_party(client, init_db, auth_header):
    with init_db.session.begin():
        party = Party(name='Test Party', description='A test party')
        init_db.session.add(party)
        init_db.session.commit()

    response = client.get(f'/parties/{party.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Test Party'


def test_update_party(client, init_db, auth_header):
    with init_db.session.begin():
        party = Party(name='Test Party', description='A test party')
        init_db.session.add(party)
        init_db.session.commit()

    data = {
        'name': 'Updated Party',
        'description': 'An updated test party'
    }
    response = client.put(f'/parties/{party.id}', json=data,
                          headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Updated Party'
    assert data['description'] == 'An updated test party'


def test_assign_user_to_party(client, init_db, auth_header):
    with init_db.session.begin():
        user = User.query.filter_by(username='testuserA').first()
        party = Party(name='Test Party', description='A test party')
        init_db.session.add(party)
        init_db.session.commit()

    data = {'party_id': party.id}
    response = client.post(f'/parties/{user.id}/assign-party', json=data,
                           headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'User assigned to party successfully'


def test_remove_user_from_party(client, init_db, auth_header):
    user = User.query.filter_by(username='testuserA').first()
    party = Party(name='Test Party', description='A test party')
    init_db.session.add(party)
    init_db.session.commit()

    user.party_id = party.id
    init_db.session.commit()

    response = client.post(f'/parties/{user.id}/remove-party',
                           headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'User removed from party successfully'


def test_get_party_users(client, init_db, auth_header):
    user = User.query.filter_by(username='testuserA').first()
    party = Party(name='Test Party', description='A test party')
    init_db.session.add(party)
    init_db.session.commit()

    user.party_id = party.id
    init_db.session.commit()

    response = client.get(f'/parties/{party.id}/users', headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['username'] == 'testuserA'
