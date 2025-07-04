from app import create_app, db
from ..models import Election
from services.participation_service import ParticipationService
from datetime import datetime

app = create_app()


def handle_completed_elections():
    """Check for completed elections and handle participation points"""
    with app.app_context():
        # Find elections that have ended but haven't been processed
        completed_elections = Election.query.filter(
            Election.end_date < datetime.utcnow(),
            Election.processed is False
        ).all()

        for election in completed_elections:
            ParticipationService.handle_election_ended(election.id)
            election.processed = True
            db.session.commit()
