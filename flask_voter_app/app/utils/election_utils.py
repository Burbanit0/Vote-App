from app import db
from app.models import Election
from datetime import datetime, timezone


def get_election_status(election):
    """
    Determine the status of an election.

    Args:
        election (Election): The election object.

    Returns:
        str: The status of the election ('upcoming', 'ongoing', 'completed').
    """
    now = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)

    # Ensure election dates are timezone-aware
    start_date = election.start_date.replace(tzinfo=timezone.utc) if election.start_date.tzinfo is None else election.start_date
    end_date = election.end_date.replace(tzinfo=timezone.utc) if election.end_date.tzinfo is None else election.end_date

    if end_date < now:
        return 'completed'
    elif start_date <= now <= end_date:
        return 'ongoing'
    else:
        return 'upcoming'


def is_election_ongoing(election):
    """
    Check if an election is currently ongoing.

    Args:
        election (Election): The election object.

    Returns:
        bool: True if the election is ongoing, False otherwise.
    """
    now = datetime.now(timezone.utc)
    # Ensure election dates are timezone-aware
    start_date = election.start_date.replace(tzinfo=timezone.utc) if election.start_date.tzinfo is None else election.start_date
    end_date = election.end_date.replace(tzinfo=timezone.utc) if election.end_date.tzinfo is None else election.end_date

    return start_date <= now <= end_date


def is_election_upcoming(election):
    """
    Check if an election is upcoming.

    Args:
        election (Election): The election object.

    Returns:
        bool: True if the election is upcoming, False otherwise.
    """
    now = datetime.now(timezone.utc)
    # Ensure election dates are timezone-aware
    start_date = election.start_date.replace(tzinfo=timezone.utc) if election.start_date.tzinfo is None else election.start_date

    return start_date > now


def is_election_completed(election):
    """
    Check if an election is completed.

    Args:
        election (Election): The election object.

    Returns:
        bool: True if the election is completed, False otherwise.
    """
    now = datetime.now(timezone.utc)
    # Ensure election dates are timezone-aware
    end_date = election.end_date.replace(tzinfo=timezone.utc) if election.end_date.tzinfo is None else election.end_date

    return end_date < now


def update_election_statuses():
    """
    Update the statuses of all elections in the database.
    """
    elections = Election.query.all()
    for election in elections:
        election.status = get_election_status(election)
    db.session.commit()
