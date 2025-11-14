# tests/test_election_utils.py
from datetime import datetime, timezone, timedelta
from app.utils.election_utils import (
    update_election_statuses,
    get_election_status,
    is_election_completed,
    is_election_ongoing,
    is_election_upcoming
)
from app.models import Election, User


def test_get_election_status(init_db):
    user = User.query.filter_by(username='testuserA').first()
    past_election = Election(
        name='Past Election',
        start_date=datetime.now(timezone.utc) - timedelta(days=3),
        end_date=datetime.now(timezone.utc) - timedelta(days=1),
        created_by=user.id
    )
    current_election = Election(
        name='Current Election',
        start_date=datetime.now(timezone.utc) - timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=1),
        created_by=user.id
    )
    future_election = Election(
        name='Future Election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=3),
        created_by=user.id
    )

    init_db.session.add_all([past_election, current_election, future_election])
    init_db.session.commit()

    assert get_election_status(past_election) == 'completed'
    assert get_election_status(current_election) == 'ongoing'
    assert get_election_status(future_election) == 'upcoming'


def test_update_election_statuses(init_db):
    user = User.query.filter_by(username='testuserA').first()
    # Create elections with different statuses
    past_election = Election(
        name='Past Election',
        description='A past election',
        start_date=datetime.now(timezone.utc) - timedelta(days=3),
        end_date=datetime.now(timezone.utc) - timedelta(days=1),
        created_by=user.id
    )
    current_election = Election(
        name='Current Election',
        description='A current election',
        start_date=datetime.now(timezone.utc) - timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=1),
        created_by=user.id
    )
    future_election = Election(
        name='Future Election',
        description='A future election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=3),
        created_by=user.id
    )

    init_db.session.add_all([past_election, current_election,
                             future_election])
    init_db.session.commit()

    # Call the function to update statuses
    update_election_statuses()

    # Check the statuses
    updated_past = init_db.session.get(Election, past_election.id)
    updated_current = init_db.session.get(Election, current_election.id)
    updated_future = init_db.session.get(Election, future_election.id)

    assert get_election_status(updated_past) == 'completed'
    assert get_election_status(updated_current) == 'ongoing'
    assert get_election_status(updated_future) == 'upcoming'


def test_election_status_checks(init_db):
    user = User.query.filter_by(username='testuserA').first()
    past_election = Election(
        name='Past Election',
        description='A past election',
        start_date=datetime.now(timezone.utc) - timedelta(days=3),
        end_date=datetime.now(timezone.utc) - timedelta(days=1),
        created_by=user.id
    )
    current_election = Election(
        name='Current Election',
        description='A current election',
        start_date=datetime.now(timezone.utc) - timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=1),
        created_by=user.id
    )
    future_election = Election(
        name='Future Election',
        description='A future election',
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=3),
        created_by=user.id
    )

    init_db.session.add_all([past_election, current_election,
                             future_election])
    init_db.session.commit()

    assert is_election_ongoing(current_election) is True
    assert is_election_upcoming(future_election) is True
    assert is_election_completed(past_election) is True
