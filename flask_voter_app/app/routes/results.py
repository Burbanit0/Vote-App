from flask import Blueprint, request, jsonify
from ..models import Result, db

bp = Blueprint('results', __name__, url_prefix='/results')

@bp.route('/', methods=['GET'])
def get_results():
    results = Result.query.all()
    return jsonify([{'id': r.id, 'candidate_id': r.candidate_id, 'vote_count': r.vote_count, 'vote_type': r.vote_type} for r in results])

@bp.route('/majority', methods=['GET'])
def get_majority():
    return

@bp.route('/condorcets', methods=['GET'])
def get_condorcets():
    return

