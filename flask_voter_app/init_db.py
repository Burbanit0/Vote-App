from app import create_app, db
from app.models import Candidate, Voter, Vote

def init_db():
    app = create_app()
    with app.app_context():
        # Create the database tables
        db.create_all()

        # Add candidates
        candidates = [
            Candidate(first_name='Alice', last_name='Smith'),
            Candidate(first_name='Bob', last_name='Johnson'),
            Candidate(first_name='Charlie', last_name='Brown')
        ]
        db.session.add_all(candidates)
        db.session.commit()

        # Add voters and their choices
        voters = []
        for i in range(1, 11):
            voter = Voter(first_name=f'Voter{i}', last_name=f'Last{i}')
            db.session.add(voter)
            db.session.commit()

            # Assign votes to each voter
            for j, candidate in enumerate(candidates):
                vote_type = 'single' if j == 0 else 'multiple' if j == 1 else 'ordered'
                vote = Vote(
                    voter_id=voter.id,
                    candidate_id=candidate.id,
                    vote_type=vote_type,
                    rank=j + 1 if vote_type == 'ordered' else None,
                    weight=33.33 if vote_type == 'weighted' else None,
                    rating=5 - j if vote_type == 'rated' else None
                )
                db.session.add(vote)
            db.session.commit()

if __name__ == '__main__':
    init_db()
