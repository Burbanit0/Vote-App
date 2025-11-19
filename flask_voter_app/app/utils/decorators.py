# app/utils/decorators.py
from functools import wraps
from app import db
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models import User, Vote, ElectionRole, user_election_roles


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or user.role != "Admin":
            return jsonify({"message": "Admin access required"}), 403

        return fn(*args, **kwargs)

    return wrapper


def election_organizer_required(fn):
    """
    Decorator to require that the user is an organizer for
    the specified election.
    Can be used for endpoints that require election organizer privileges.
    """

    @wraps(fn)
    def wrapper(election_id, *args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"message": "User not found"}), 404

        # Check if user is an admin
        if user.role == "Admin":
            return fn(election_id, *args, **kwargs)

        # Check if user is an organizer for this election
        is_organizer = (
            db.session.query(user_election_roles)
            .filter(
                user_election_roles.c.user_id == user_id,
                user_election_roles.c.election_id == election_id,
                user_election_roles.c.role == ElectionRole.ORGANIZER,
            )
            .first()
        )

        if not is_organizer:
            return jsonify({"message": "Election organizer access required"}), 403

        return fn(election_id, *args, **kwargs)

    return wrapper


def candidate_eligible_required(fn):
    """
    Decorator to require that the user meets the participation requirements
    to be a candidate.
    """

    @wraps(fn)
    def wrapper(election_id, *args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"message": "User not found"}), 404

        # Check if user meets the participation requirements to be a candidate
        if user.elections_participated < 10:
            return (
                jsonify(
                    {
                        "message": f"User must have participated in at least \
                            10 elections to be a candidate. "
                        f"Current participation: \
                            {user.elections_participated}"
                    }
                ),
                403,
            )

        return fn(election_id, *args, **kwargs)

    return wrapper


def organizer_eligible_required(fn):
    """
    Decorator to require that the user meets the participation requirements to
    be an organizer.
    """

    @wraps(fn)
    def wrapper(election_id, *args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"message": "User not found"}), 404

        # Check if user meets the participation requirements to be an organizer
        if user.elections_participated < 15:
            return (
                jsonify(
                    {
                        "message": f"User must have participated in at least \
                           15 elections to be an organizer. "
                        f"Current participation: \
                           {user.elections_participated}"
                    }
                ),
                403,
            )

        # Check if user has voted in enough elections
        voted_elections_count = (
            db.session.query(Vote.election_id)
            .filter(Vote.voter_id == user_id)
            .distinct()
            .count()
        )

        if voted_elections_count < 5:
            return (
                jsonify(
                    {
                        "message": f"User must have voted in at least \
                           5 elections to be an organizer. "
                        f"Current votes cast: {voted_elections_count}"
                    }
                ),
                403,
            )

        return fn(election_id, *args, **kwargs)

    return wrapper


def not_candidate_in_election(fn):
    """
    Decorator to ensure the user is not already a candidate in
    the specified election.
    """

    @wraps(fn)
    def wrapper(election_id, *args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()

        # Check if user is already a candidate in this election
        existing_candidate_role = (
            db.session.query(user_election_roles)
            .filter(
                user_election_roles.c.user_id == user_id,
                user_election_roles.c.election_id == election_id,
                user_election_roles.c.role == ElectionRole.CANDIDATE,
            )
            .first()
        )

        if existing_candidate_role:
            return (
                jsonify({"message": "User is already a candidate in this election"}),
                400,
            )

        return fn(election_id, *args, **kwargs)

    return wrapper


def not_organizer_in_election(fn):
    """
    Decorator to ensure the user is not already an organizer
    in the specified election.
    """

    @wraps(fn)
    def wrapper(election_id, *args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()

        # Check if user is already an organizer in this election
        existing_organizer_role = (
            db.session.query(user_election_roles)
            .filter(
                user_election_roles.c.user_id == user_id,
                user_election_roles.c.election_id == election_id,
                user_election_roles.c.role == ElectionRole.ORGANIZER,
            )
            .first()
        )

        if existing_organizer_role:
            return (
                jsonify({"message": "User is already an organizer in this election"}),
                400,
            )

        return fn(election_id, *args, **kwargs)

    return wrapper
