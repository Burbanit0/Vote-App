# services/participation_service.py
from app.models import User, Election, Vote, user_election_roles
from app import db


class ParticipationService:
    @staticmethod
    def add_participation_points(user_id, points, reason):
        """Add participation points to a user"""
        user = User.query.get(user_id)
        if user:
            user.participation_points += points
            db.session.commit()
            return True
        return False

    @staticmethod
    def subtract_participation_points(user_id, points, reason):
        """Subtract participation points from a user"""
        user = User.query.get(user_id)
        if user:
            # Ensure points don't go below 0
            user.participation_points = max(0,
                                            user.participation_points - points)
            db.session.commit()
            return True
        return False

    @staticmethod
    def handle_election_participation(user_id, election_id, role):
        """Handle participation points when a user joins an election"""
        points = 0

        if role == 'organizer':
            points = 25
        elif role == 'candidate':
            points = 5
        elif role == 'voter':
            points = 1

        if points > 0:
            ParticipationService.add_participation_points(
                user_id,
                points,
                f"Joined election {election_id} as {role}"
            )

    @staticmethod
    def handle_vote_cast(user_id, election_id):
        """Handle participation points when a user votes"""
        # Check if user is a participant in this election
        is_participant = db.session.query(
            db.session.query(user_election_roles)
            .filter(
                user_election_roles.c.user_id == user_id,
                user_election_roles.c.election_id == election_id
            )
            .exists()
        ).scalar()

        if is_participant:
            # Add 1 point for voting
            ParticipationService.add_participation_points(
                user_id,
                1,
                f"Voted in election {election_id}"
            )

    @staticmethod
    def handle_election_ended(election_id):
        """Handle participation points when an election ends"""
        election = Election.query.get(election_id)
        if not election:
            return

        # Find all participants who didn't vote
        participants = db.session.query(user_election_roles.c.user_id).filter(
            user_election_roles.c.election_id == election_id
        ).all()

        for participant in participants:
            user_id = participant.user_id

            # Check if this user voted
            has_voted = db.session.query(
                db.session.query(Vote)
                .filter(
                    Vote.voter_id == user_id,
                    Vote.election_id == election_id
                )
                .exists()
            ).scalar()

            if not has_voted:
                # Get the user's role in this election
                role = db.session.query(user_election_roles.c.role).filter(
                    user_election_roles.c.user_id == user_id,
                    user_election_roles.c.election_id == election_id
                ).scalar()

                role = role.value if role else str(role)

                # Subtract points based on role
                if role == 'candidate':
                    ParticipationService.subtract_participation_points(
                        user_id,
                        5,
                        f"Did not vote in election {election_id} as candidate"
                    )
                elif role == 'voter':
                    ParticipationService.subtract_participation_points(
                        user_id,
                        1,
                        f"Did not vote in election {election_id} as voter"
                    )
