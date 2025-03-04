from flask import Blueprint, jsonify
from ..models import Result, Candidate, db

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

@bp.route('/condorcets', methods=['GET'])
def get_condorcets():
    
    results = db.session.query(
        Result,
        Candidate.first_name,
        Candidate.last_name
    ).join(
        Candidate, Result.candidate_id == Candidate.id
    ).filter(Result.vote_type == "ordered"
    ).all()

    result_list = []
    for result, first_name, last_name in results:
        result_info = {
            'candidate_id': result.candidate_id,
            'candidate_name': f'{first_name} {last_name}',
            'vote_type': result.vote_type,
            'result': result.vote_count
        }
        result_list.append(result_info)
    return jsonify(result_list)
