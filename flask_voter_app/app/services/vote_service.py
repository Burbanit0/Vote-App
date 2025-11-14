# app/services/vote_service.py
from app import db
from app.models import Vote, User, ElectionRole, Election, user_election_roles
from datetime import datetime
from ..services.participation_service import ParticipationService


class VoteService:
    @staticmethod
    def cast_vote(user_id, election_id, candidate_id):
        election = Election.query.get_or_404(election_id)
        if not election or election.start_date > datetime.utcnow():
            return {"message": "Election has not started yet"}, 400

        if election.end_date <= datetime.utcnow():
            return {"message": "Election has already ended"}, 400

        candidate_role = (
            db.session.query(user_election_roles)
            .filter(
                user_election_roles.c.user_id == candidate_id,
                user_election_roles.c.election_id == election_id,
                user_election_roles.c.role == ElectionRole.CANDIDATE,
            )
            .first()
        )

        if not candidate_role:
            return {
                "message": "Candidate not found or not participating in this election"
            }, 404

        voter_role = (
            db.session.query(user_election_roles)
            .filter(
                user_election_roles.c.user_id == user_id,
                user_election_roles.c.election_id == election_id,
            )
            .first()
        )

        if not voter_role:
            return {"message": "User is not a voter in this election"}, 403

        has_voted = db.session.query(
            db.session.query(user_election_roles)
            .filter(
                user_election_roles.c.user_id == user_id,
                user_election_roles.c.election_id == election_id,
                user_election_roles.c.has_voted.is_(True),
            )
            .exists()
        ).scalar()

        if has_voted:
            return {"message": "User has already voted in this election"}, 400

        vote = Vote(
            voter_id=user_id,
            candidate_id=candidate_id,
            election_id=election_id,
            cast_at=datetime.utcnow(),
        )

        db.session.execute(
            user_election_roles.update()
            .where(
                user_election_roles.c.user_id == user_id,
                user_election_roles.c.election_id == election_id,
            )
            .values(has_voted=True)
        )

        ParticipationService.handle_vote_cast(user_id, election_id)

        db.session.add(vote)
        db.session.commit()

        return {"message": "Vote cast successfully", "vote_id": vote.id}

    @staticmethod
    def get_election_results(election_id):
        election = Election.query.get_or_404(election_id)
        if election.end_date > datetime.utcnow():
            return {"message": "Election has not ended yet"}, 400

        votes = (
            db.session.query(
                Vote.candidate_id,
                User.first_name,
                User.last_name,
                db.func.count(Vote.id).label("vote_count"),
            )
            .join(User, Vote.candidate_id == User.id)
            .filter(Vote.election_id == election_id)
            .group_by(Vote.candidate_id, User.first_name, User.last_name)
            .all()
        )

        results = [
            {
                "candidate_id": candidate_id,
                "candidate_name": f"{first_name} {last_name}",
                "vote_count": vote_count,
            }
            for candidate_id, first_name, last_name, vote_count in votes
        ]

        results.sort(key=lambda x: x["vote_count"], reverse=True)

        return {"election_id": election_id, "results": results}
