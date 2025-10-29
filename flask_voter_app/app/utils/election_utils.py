from app import db
from app.models import Election
from datetime import datetime


def update_election_statuses():
    now = datetime.utcnow()
    elections = Election.query.all()
    for election in elections:
        if election.end_date and now > election.end_date:
            election.status = "Completed"
        elif election.start_date and now >= election.start_date:
            election.status = "Ongoing"
        else:
            election.status = "Upcoming"
    db.session.commit()
    print(f"Updated status for {len(elections)} elections at {now}")
