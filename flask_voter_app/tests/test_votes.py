# tests/test_votes.py
from datetime import datetime, timedelta, timezone
from app.models import ElectionRole, User, Election, user_election_roles


def test_cast_vote(client, init_db, auth_header):
    user = User.query.filter_by(username='testuserA').first()
    election = Election(
        name='Test Election',
        description='A test election',
        start_date=datetime.now(timezone.utc) - timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=1),
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

    # Update user role to candidate
    init_db.session.execute(
        user_election_roles.update()
        .where(
            user_election_roles.c.user_id == user.id,
            user_election_roles.c.election_id == election.id
        )
        .values(role=ElectionRole.CANDIDATE)
    )
    init_db.session.commit()

    # Cast a vote
    data = {'candidate_id': user.id}
    response = client.post(f'/votes/elections/{election.id}', json=data,
                           headers=auth_header)
    print(response.data)
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Vote cast successfully'


def test_get_election_results(client, init_db, auth_header):
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

    init_db.session.execute(
        user_election_roles.insert().values(
            user_id=user.id,
            election_id=election.id,
            role=ElectionRole.ORGANIZER
        )
    )
    init_db.session.commit()

    response = client.get(f'/votes/elections/{election.id}/results',
                          headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()
    assert data['election_id'] == election.id
