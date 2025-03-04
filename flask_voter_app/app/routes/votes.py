from flask import Blueprint, request, jsonify, current_app
from ..models import Vote, Result, Candidate, db

bp = Blueprint('votes', __name__, url_prefix='/votes')

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
            ).filter(Vote.vote_type == vote_type[0]).group_by(Vote.candidate_id).all()

            # Store results in the result table
            for Candidate, vote_count in results:
                result = Result(candidate_name=Candidate.first_name, vote_count=vote_count, vote_type=vote_type[0])
                db.session.add(result)

        db.session.commit()

@bp.route('/', methods=['POST'])
def create_vote():
    data = request.get_json()
    voter_id = data.get('voter_id')
    candidate_id = data.get('candidate_id')
    vote_type = data.get('vote_type')
    rank = data.get('rank')
    weight = data.get('weight')
    rating = data.get('rating')

    if not voter_id or not candidate_id or not vote_type:
        return jsonify({'error': 'Voter ID, Candidate ID, and Vote Type are required'}), 400

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

    update_results()

    return jsonify({
        'id': new_vote.id,
        'voter_id': new_vote.voter_id,
        'candidate_id': new_vote.candidate_id,
        'vote_type': new_vote.vote_type,
        'rank': new_vote.rank,
        'weight': new_vote.weight,
        'rating': new_vote.rating
    }), 201

@bp.route('/<int:vote_id>', methods=['PUT'])
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

@bp.route('/<int:vote_id>', methods=['DELETE'])
def delete_vote(vote_id):
    vote = Vote.query.get_or_404(vote_id)
    db.session.delete(vote)
    db.session.commit()

    return jsonify({'result': True})

@bp.route('/', methods=['GET'])
def get_votes():
    votes = Vote.query.all()
    return jsonify([{
        'id':v.id, 
        'voter_id':v.voter_id, 
        'candidate_id':v.candidate_id, 
        'vote_type':v.vote_type, 
        'rank':v.rank, 
        'weight':v.weight, 
        'rating':v.rating
    } for v in votes])