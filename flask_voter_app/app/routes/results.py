from flask import Blueprint, jsonify
from app.utils.utils import get_condorcet_winner
from ..models import Result, Candidate, Vote, db

bp = Blueprint('results', __name__, url_prefix='/results')

@bp.route('/', methods=['GET'])
def get_results():
    results = Result.query.all()
    return jsonify([{'id': r.id, 'candidate_id': r.candidate_id, 'vote_count': r.vote_count, 'vote_type': r.vote_type} for r in results])

@bp.route('/majority', methods=['GET'])
def get_majority():
    total_sum = db.session.query(db.func.sum(Result.vote_count)).filter(Result.vote_type == 'single').scalar()
    if total_sum is None:
        total_sum = 0  # Handle the case where there are no votes
    
    results = db.session.query(
        Result,
        Candidate.first_name,
        Candidate.last_name
    ).join(
        Candidate, Result.candidate_id == Candidate.id
    ).filter(Result.vote_type == "single"
    ).all()

    result_list = []
    for result, first_name, last_name in results:
        result_info = {
            'candidate_id': result.candidate_id,
            'candidate_name': f'{first_name} {last_name}',
            'vote_type': result.vote_type,
            'result': (result.vote_count / total_sum * 100) if total_sum != 0 else 0
        }
        result_list.append(result_info)
    return jsonify(result_list)

@bp.route('/condorcet', methods=['GET'])
def get_condorcet():
    all_votes = db.session.query(Vote).all()
    print(all_votes)
    winner = get_condorcet_winner(all_votes) ## return a candidate_id
    candidates = db.session.query(Candidate).filter(Candidate.id == winner)
    
    result_list = []
    for candidate in candidates:
        result_info = {'first_name' : candidate.first_name,
                       'last_name' : candidate.last_name,
                       'id' : candidate.id}
        result_list.append(result_info)

    return jsonify(result_list[0])