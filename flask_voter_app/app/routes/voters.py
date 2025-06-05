from flask import Blueprint, request, jsonify
from ..models import Voter, Vote, Candidate, db

bp = Blueprint('voters', __name__, url_prefix='/voters')


@bp.route('/', methods=['GET'])
def get_voters():
    voters = Voter.query.all()
    return jsonify([{'id': v.id, 'first_name': v.first_name,
                    'last_name': v.last_name} for v in voters])


@bp.route('/', methods=['POST'])
def create_voter():
    data = request.get_json()
    user_id = data.get('user_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    if not first_name or not last_name or not user_id:
        return jsonify({
            'error': 'First name and last name and user id are required'}), 400

    new_voter = Voter(first_name=first_name, last_name=last_name,
                      user_id=user_id)
    db.session.add(new_voter)
    db.session.commit()

    return jsonify({'id': new_voter.id,
                    'first_name': new_voter.first_name,
                    'last_name': new_voter.last_name,
                    'user_id': new_voter.user_id}), 201


@bp.route('/<int:voter_id>', methods=['PUT'])
def update_voter(voter_id):
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    voter = Voter.query.get_or_404(voter_id)

    if first_name:
        voter.first_name = first_name
    if last_name:
        voter.last_name = last_name

    db.session.commit()

    return jsonify({'id': voter.id, 'first_name': voter.first_name,
                    'last_name': voter.last_name})


@bp.route('/<int:voter_id>', methods=['DELETE'])
def delete_voter(voter_id):
    voter = Voter.query.get_or_404(voter_id)
    db.session.delete(voter)
    db.session.commit()

    return jsonify({'result': True})


# for different types of votes
@bp.route('/<int:voter_id>/votes', methods=['GET'])
def get_voter_votes(voter_id):
    votes = db.session.query(Vote, Candidate).join(Candidate,
                                                   Vote.candidate_id ==
                                                   Candidate.id).filter(
                                                       Vote.voter_id ==
                                                       voter_id).all()

    vote_results = []
    for vote, candidate in votes:
        vote_info = {
            'candidate_id': candidate.id,
            'candidate_name': f'{candidate.first_name} {candidate.last_name}',
            'vote_type': vote.vote_type,
        }
        if vote.vote_type == 'ordered':
            vote_info['rank'] = vote.rank
        elif vote.vote_type == 'weighted':
            vote_info['weight'] = vote.weight
        elif vote.vote_type == 'rated':
            vote_info['rating'] = vote.rating
        vote_results.append(vote_info)

    return jsonify(vote_results)


# API Endpoint to get voters with their single choice
@bp.route('/single-choice', methods=['GET'])
def get_voters_with_single_choice():
    # Query to get voters and their single choice vote
    voters_with_choices = db.session.query(
        Voter,
        Candidate.id
    ).join(
        Vote, Voter.id == Vote.voter_id
    ).join(
        Candidate, Vote.candidate_id == Candidate.id
    ).filter(
        Vote.vote_type == 'single'  # Adjust the filter based on your vote type
    ).all()

    # Prepare the response
    voter_list = []
    for voter, id in voters_with_choices:
        voter_info = {
            'voter_id': voter.id,
            'voter_first_name': voter.first_name,
            'voter_last_name': voter.last_name,
            'choice': id
        }
        voter_list.append(voter_info)

    return jsonify(voter_list)


@bp.route('/multiple-choices', methods=['GET'])
def get_voters_with_mutliple_choices():
    voters_with_choices = db.session.query(
        Voter,
        Candidate.id
    ).join(
        Vote, Voter.id == Vote.voter_id
    ).join(
        Candidate, Vote.candidate_id == Candidate.id
    ).filter(
        Vote.vote_type == 'multiple'
    ).all()

    # Prepare the response
    voter_list = []
    for voter, id in voters_with_choices:
        voter_info = {
            'voter_id': voter.id,
            'voter_first_name': voter.first_name,
            'voter_last_name': voter.last_name,
            'choice': id
        }
        voter_list.append(voter_info)

    return jsonify(voter_list)


@bp.route('/ranked', methods=['GET'])
def get_voters_with_ranked():
    voters_with_ranked = db.session.query(
        Voter,
        Candidate.id
    ).join(
        Vote, Voter.id == Vote.voter_id
    ).join(
        Candidate, Vote.candidate_id == Candidate.id
    ).filter(
        Vote.vote_type == 'ordered'
    ).all()

    # Prepare the response
    voter_list = []
    for voter, id in voters_with_ranked:
        voter_info = {
            'voter_id': voter.id,
            'voter_first_name': voter.first_name,
            'voter_last_name': voter.last_name,
            'choice': id
        }
        voter_list.append(voter_info)

    return jsonify(voter_list)


@bp.route('/weighted', methods=['GET'])
def get_voters_with_weight():
    voters_with_weight = db.session.query(
        Voter,
        Candidate.id
    ).join(
        Vote, Voter.id == Vote.voter_id
    ).join(
        Candidate, Vote.candidate_id == Candidate.id
    ).filter(
        Vote.vote_type == 'weighted'
    ).all()

    # Prepare the response
    voter_list = []
    for voter, id in voters_with_weight:
        voter_info = {
            'voter_id': voter.id,
            'voter_first_name': voter.first_name,
            'voter_last_name': voter.last_name,
            'choice': id
        }
        voter_list.append(voter_info)

    return jsonify(voter_list)


@bp.route('/rate', methods=['GET'])
def get_voters_with_rate():
    voters_with_rated = db.session.query(
        Voter,
        Candidate.id
    ).join(
        Vote, Voter.id == Vote.voter_id
    ).join(
        Candidate, Vote.candidate_id == Candidate.id
    ).filter(
        Vote.vote_type == 'rated'  # Adjust the filter based on your vote type
    ).all()

    # Prepare the response
    voter_list = []
    for voter, id in voters_with_rated:
        voter_info = {
            'voter_id': voter.id,
            'voter_first_name': voter.first_name,
            'voter_last_name': voter.last_name,
            'choice': id
        }
        voter_list.append(voter_info)

    return jsonify(voter_list)
