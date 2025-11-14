# app/api/votes.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Vote, Result
from app import db
from app.utils.decorators import election_organizer_required
from ..services.vote_service import VoteService

vote_bp = Blueprint('votes', __name__, url_prefix='/votes')


@vote_bp.route('/elections/<int:election_id>', methods=['POST'])
@jwt_required()
def cast_vote(election_id):
    """Cast a vote in an election"""
    user_id = get_jwt_identity()
    data = request.get_json()
    candidate_id = data.get('candidate_id')
    result = VoteService.cast_vote(user_id, election_id, candidate_id)
    return jsonify(result), 200


@vote_bp.route('/elections/<int:election_id>/results', methods=['GET'])
@election_organizer_required
def get_election_results(election_id):
    """Get results for an election - organizer or admin only"""
    # Get all votes for this election
    result = VoteService.get_election_results(election_id)
    return jsonify(result)


def update_results():
    with current_app.app_context():
        # Clear existing results
        db.session.query(Result).delete()

        # Calculate results for each vote type
        vote_types = db.session.query(Vote.vote_type).distinct().all()
        for vote_type in vote_types:
            results = db.session.query(
                Vote.candidate_id,
                db.func.count(Vote.id).label('vote_count')
            ).filter(Vote.vote_type == vote_type[0]).group_by(
                Vote.candidate_id).all()

            # Store results in the result table
            for Candidate, vote_count in results:
                result = Result(candidate_name=Candidate.first_name,
                                vote_count=vote_count, vote_type=vote_type[0])
                db.session.add(result)

        db.session.commit()


# POST routes
@vote_bp.route('/', methods=['POST'])
def create_vote():
    data = request.get_json()
    voter_id = data.get('voter_id')
    candidate_id = data.get('candidate_id')
    vote_type = data.get('vote_type')
    rank = data.get('rank')
    weight = data.get('weight')
    rating = data.get('rating')

    if not voter_id or not candidate_id or not vote_type:
        return jsonify({
            'error': 'Voter ID, Candidate ID, and Vote Type are required'}),
        400

    # Check if the voter has already voted for this candidate
    existing_vote = Vote.query.filter_by(
        voter_id=voter_id,
        candidate_id=candidate_id).first()
    if existing_vote:
        return jsonify({"msg": "Voter has already voted for this candidate."}),
    400

    # Check if the rank is already used by the voter
    existing_rank = Vote.query.filter_by(voter_id=voter_id, rank=rank).first()
    if existing_rank:
        return jsonify({"msg": "Rank is already used by this voter."}), 400

    new_vote = Vote(
        voter_id=voter_id,
        candidate_id=candidate_id,
        vote_type=vote_type,
        rank=rank,
        weight=weight,
        rating=rating
    )
    db.session.add(new_vote)
    db.session.commit()

    # update_results()
    return jsonify({
        'id': new_vote.id,
        'voter_id': new_vote.voter_id,
        'candidate_id': new_vote.candidate_id,
        'vote_type': new_vote.vote_type,
        'rank': new_vote.rank,
        'weight': new_vote.weight,
        'rating': new_vote.rating
    }), 201


# PUT routes
@vote_bp.route('/<int:vote_id>', methods=['PUT'])
def update_vote(vote_id):
    data = request.get_json()
    vote_type = data.get('vote_type')
    rank = data.get('rank')
    weight = data.get('weight')
    rating = data.get('rating')

    vote = Vote.query.get_or_404(vote_id)

    if vote_type:
        vote.vote_type = vote_type
    if rank is not None:
        vote.rank = rank
    if weight is not None:
        vote.weight = weight
    if rating is not None:
        vote.rating = rating

    db.session.commit()

    return jsonify({
        'id': vote.id,
        'voter_id': vote.voter_id,
        'candidate_id': vote.candidate_id,
        'vote_type': vote.vote_type,
        'rank': vote.rank,
        'weight': vote.weight,
        'rating': vote.rating
    })


# DELETE routes:
@vote_bp.route('/<int:vote_id>', methods=['DELETE'])
def delete_vote(vote_id):
    vote = Vote.query.get_or_404(vote_id)
    db.session.delete(vote)
    db.session.commit()

    return jsonify({'result': True})


@vote_bp.route('/voter/<int:voter_id>', methods=['DELETE'])
def delete_voter_votes(voter_id):
    # Find all votes for the specified voter
    votes = Vote.query.filter_by(voter_id=voter_id).all()

    if not votes:
        return jsonify({"msg": "No votes found for this voter."}), 404

    # Delete all votes for the specified voter
    for vote in votes:
        db.session.delete(vote)

    db.session.commit()
    return jsonify({"msg": "All votes for the voter have been deleted."}), 200


# GET routes:
@vote_bp.route('/', methods=['GET'])
def get_votes():
    votes = Vote.query.all()
    return jsonify([{
        'id': v.id,
        'voter_id': v.voter_id,
        'candidate_id': v.candidate_id,
        'vote_type': v.vote_type,
        'rank': v.rank,
        'weight': v.weight,
        'rating': v.rating
    } for v in votes])


@vote_bp.route('/voter/<int:voter_id>', methods=['GET'])
def get_voter_votes(voter_id):
    # Query the database for all votes associated with the specified voter
    votes = Vote.query.filter_by(voter_id=voter_id).all()

    if not votes:
        return jsonify({"msg": "No votes found for this voter."}), 404

    # Prepare the votes data to be sent as JSON
    votes_data = [
        {
            'id': vote.id,
            'candidate_id': vote.candidate_id,
            'vote_type': vote.vote_type,
            'rank': vote.rank,
            'created_at': vote.created_at.isoformat()
        }
        for vote in votes
    ]

    return jsonify(votes_data), 200


@vote_bp.route('/candidate/<int:candidate_id>', methods=['GET'])
def get_candidate_votes(candidate_id):
    # Query the database for all votes associated with the specified candidate
    votes = Vote.query.filter_by(candidate_id=candidate_id).all()

    if not votes:
        return jsonify({"msg": "No votes found for this candidate."}), 404

    # Prepare the votes data to be sent as JSON
    votes_data = [
        {
            'id': vote.id,
            'voter_id': vote.voter_id,
            'vote_type': vote.vote_type,
            'rank': vote.rank,
            'created_at': vote.created_at.isoformat()
        }
        for vote in votes
    ]

    return jsonify(votes_data), 200
