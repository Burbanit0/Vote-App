# tests/test_elections.py
from datetime import datetime, timedelta, timezone
from app.models import Election, User, ElectionRole, user_election_roles


def test_get_all_elections_empty(client, init_db):
    """Test GET /elections/ with no elections"""
    response = client.get('/elections/')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] == 0
    assert len(data['elections']) == 0


def test_create_election(client, init_db, auth_header):
    """Test POST /elections/"""
    data = {
        'name': 'Test Election',
        'description': 'A test election',
        'start_date': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        'end_date': (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    }
    response = client.post('/elections/', json=data, headers=auth_header)
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Test Election'
    assert 'id' in data


def test_get_election(client, init_db, auth_header):
    """Test GET /elections/<id>"""
    # Create a test election
    user = User.query.filter_by(username='testuserA').first()
    election = Election(
        name='Test Election',
        description='A test election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=2),
        created_by=user.id
    )
    init_db.session.add(election)
    init_db.session.commit()

    # Add user as organizer
    init_db.session.execute(
        user_election_roles.insert().values(
            user_id=user.id,
            election_id=election.id,
            role=ElectionRole.ORGANIZER
        )
    )
    init_db.session.commit()

    response = client.get(f'/elections/{election.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Test Election'
    assert data['created_by']['id'] == user.id


def test_get_election_participants(client, init_db, auth_header):
    """Test GET /elections/<id>/participants"""
    user = User.query.filter_by(username='testuserA').first()
    election = Election(
        name='Test Election',
        description='A test election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=2),
        created_by=user.id
    )
    init_db.session.add(election)
    init_db.session.commit()

    # Add user as organizer
    init_db.session.execute(
        user_election_roles.insert().values(
            user_id=user.id,
            election_id=election.id,
            role=ElectionRole.ORGANIZER
        )
    )
    init_db.session.commit()

    response = client.get(f'/elections/{election.id}/participants')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['user_id'] == user.id
    assert data[0]['role'] == 'organizer'


def test_participate_in_election(client, init_db, auth_header):
    """Test POST /elections/<id>/participate"""
    with init_db.session.begin():
        user = User.query.filter_by(username='testuserA').first()
        election = Election(
            name='Test Election',
            description='A test election',
            start_date=datetime.now(timezone.utc) + timedelta(days=1),
            end_date=datetime.now(timezone.utc) + timedelta(days=2),
            created_by=user.id
        )
        init_db.session.add(election)
        init_db.session.commit()

    data = {'role': 'voter'}
    response = client.post(f'/elections/{election.id}/participate', json=data,
                           headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Successfully joined the election as a voter'


def test_register_as_candidate(client, init_db, auth_header):
    """Test POST /elections/<id>/register-candidate"""

    user = User.query.filter_by(username='testuserA').first()
    election = Election(
        name='Test Election',
        description='A test election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=2),
        created_by=user.id
    )
    init_db.session.add(election)
    init_db.session.commit()

    # Add user as voter first
    init_db.session.execute(
        user_election_roles.insert().values(
            user_id=user.id,
            election_id=election.id,
            role=ElectionRole.VOTER
        )
    )
    init_db.session.commit()

    # Ensure the user meets the eligibility criteria
    user.elections_participated = 10  # Assuming this is the requirement
    init_db.session.commit()

    response = client.post(f'/elections/{election.id}/register-candidate',
                           headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Successfully registered as candidate in election'


def test_check_election_participation(client, init_db, auth_header):
    """Test GET /elections/<id>/participation"""
    user = User.query.filter_by(username='testuserA').first()
    election = Election(
        name='Test Election',
        description='A test election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=2),
        created_by=user.id
    )
    init_db.session.add(election)
    init_db.session.commit()

    # Add user as voter
    init_db.session.execute(
        user_election_roles.insert().values(
            user_id=user.id,
            election_id=election.id,
            role=ElectionRole.VOTER
        )
    )
    init_db.session.commit()

    response = client.get(f'/elections/{election.id}/participation',
                          headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['is_participant'] is True
    assert data['role'] == 'voter'


def test_cancel_participation(client, init_db, auth_header):
    """Test POST /elections/<id>/cancel-participation"""
    user = User.query.filter_by(username='testuserA').first()
    election = Election(
        name='Test Election',
        description='A test election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=2),
        created_by=user.id
    )
    init_db.session.add(election)
    init_db.session.commit()

    # Add user as voter
    init_db.session.execute(
        user_election_roles.insert().values(
            user_id=user.id,
            election_id=election.id,
            role=ElectionRole.VOTER
        )
    )
    init_db.session.commit()

    response = client.post(f'/elections/{election.id}/cancel-participation',
                           headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Successfully canceled participation in election'


def test_update_election(client, init_db, auth_header):
    """Test PUT /elections/<id>"""
    user = User.query.filter_by(username='testuserA').first()
    election = Election(
        name='Test Election',
        description='A test election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=2),
        created_by=user.id
    )
    init_db.session.add(election)
    init_db.session.commit()

    # Add user as organizer
    init_db.session.execute(
        user_election_roles.insert().values(
            user_id=user.id,
            election_id=election.id,
            role=ElectionRole.ORGANIZER
        )
    )
    init_db.session.commit()

    data = {
        'name': 'Updated Election',
        'description': 'An updated test election'
    }
    response = client.put(f'/elections/{election.id}', json=data,
                          headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Election updated successfully'
    assert data['election']['name'] == 'Updated Election'
    assert data['election']['description'] == 'An updated test election'


def test_delete_election(client, init_db, auth_header):
    """Test DELETE /elections/<id>"""
    user = User.query.filter_by(username='testuserA').first()
    election = Election(
        name='Test Election',
        description='A test election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=2),
        created_by=user.id
    )
    init_db.session.add(election)
    init_db.session.commit()

    # Add user as organizer
    init_db.session.execute(
        user_election_roles.insert().values(
            user_id=user.id,
            election_id=election.id,
            role=ElectionRole.ORGANIZER
        )
    )
    init_db.session.commit()

    response = client.delete(f'/elections/{election.id}', headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['result'] is True


def test_get_election_results(client, init_db, auth_header):
    """Test GET /elections/<id>/results"""
    user = User.query.filter_by(username='testuserA').first()
    election = Election(
        name='Test Election',
        description='A test election',
        start_date=datetime.now(timezone.utc) - timedelta(days=2),
        end_date=datetime.now(timezone.utc) - timedelta(days=1),
        created_by=user.id
    )
    init_db.session.add(election)
    init_db.session.commit()

    # Add user as organizer
    init_db.session.execute(
        user_election_roles.insert().values(
            user_id=user.id,
            election_id=election.id,
            role=ElectionRole.ORGANIZER
        )
    )
    init_db.session.commit()

    response = client.get(f'/elections/{election.id}/results',
                          headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['election_id'] == election.id
