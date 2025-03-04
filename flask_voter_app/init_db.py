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


import random
from faker import Faker  # Using Faker to generate realistic names
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Candidate, Voter, Vote, Base  # Adjust the import according to your project structure

# # Initialize Faker and database
# fake = Faker()
# engine = create_engine('sqlite:///election.db')
# Session = sessionmaker(bind=engine)
# session = Session()

# # Create tables
# Base.metadata.create_all(engine)

# def generate_candidates(num_candidates):
#     candidates = []
#     for _ in range(num_candidates):
#         first_name = fake.first_name()
#         last_name = fake.last_name()
#         candidate = Candidate(first_name=first_name, last_name=last_name)
#         candidates.append(candidate)
#         session.add(candidate)
#     session.commit()
#     return candidates

# def generate_voters(num_voters):
#     voters = []
#     for _ in range(num_voters):
#         first_name = fake.first_name()
#         last_name = fake.last_name()
#         voter = Voter(first_name=first_name, last_name=last_name)
#         voters.append(voter)
#         session.add(voter)
#     session.commit()
#     return voters

# def simulate_voting(voters, candidates):
#     vote_types = ['single', 'ranked']  # Add more vote types as needed
#     for voter in voters:
#         for vote_type in vote_types:
#             if vote_type == 'single':
#                 candidate = random.choice(candidates)
#                 vote = Vote(voter_id=voter.id, candidate_id=candidate.id, vote_type=vote_type)
#                 session.add(vote)
#             elif vote_type == 'ranked':
#                 ranked_candidates = candidates.copy()
#                 random.shuffle(ranked_candidates)
#                 for rank, candidate in enumerate(ranked_candidates, start=1):
#                     vote = Vote(voter_id=voter.id, candidate_id=candidate.id, vote_type=vote_type, rank=rank)
#                     session.add(vote)
#     session.commit()

# # Generate candidates and voters
# candidates = generate_candidates(num_candidates=5)
# voters = generate_voters(num_voters=100)

# # Simulate voting
# simulate_voting(voters, candidates)