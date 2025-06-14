from flask import Blueprint, request, jsonify
from ..models import Candidate, Result, db
from app import redis_client
import json

bp = Blueprint('candidates', __name__, url_prefix='/candidates')


@bp.route('/', methods=['GET'])
def get_candidates():
    cache_key = 'candidates_data'

    cached_result = redis_client.get(cache_key)

    if cached_result:
        return jsonify(json.loads(cached_result))

    candidates = Candidate.query.all()
    data = [{'id': c.id, 'first_name': c.first_name,
             'last_name': c.last_name} for c in candidates]

    redis_client.setex(cache_key, 3600, json.dumps(data))

    return jsonify(data)


@bp.route('/', methods=['POST'])
def create_candidate():
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    if not first_name or not last_name:
        return jsonify({'error': 'First name and last name are required'}), 400

    new_candidate = Candidate(first_name=first_name, last_name=last_name)
    db.session.add(new_candidate)
    db.session.commit()

    return jsonify({'id': new_candidate.id,
                    'first_name': new_candidate.first_name,
                    'last_name': new_candidate.last_name}), 201


@bp.route('/<int:candidate_id>', methods=['GET'])
def get_candidate_by_id(candidate_id):
    candidate = Candidate.query.get(candidate_id)
    if not candidate:
        return jsonify({"msg": "No candidate found with this id"}), 404
    return jsonify({
        'id': candidate.id,
        'first_name': candidate.first_name,
        'last_name': candidate.last_name
    }), 200


@bp.route('/<int:candidate_id>', methods=['PUT'])
def update_candidate(candidate_id):
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    candidate = Candidate.query.get_or_404(candidate_id)

    if first_name:
        candidate.first_name = first_name
    if last_name:
        candidate.last_name = last_name

    db.session.commit()

    return jsonify({'id': candidate.id, 'first_name': candidate.first_name,
                    'last_name': candidate.last_name})


@bp.route('/<int:candidate_id>', methods=['DELETE'])
def delete_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    db.session.delete(candidate)
    db.session.commit()

    return jsonify({'result': True})


# API Endpoint to get results for a specific candidate
@bp.route('/<int:candidate_id>/results', methods=['GET'])
def get_candidate_results(candidate_id):
    # Query the result table for the specific candidate
    results = db.session.query(
        Result,
        Candidate.first_name,
        Candidate.last_name
    ).join(
        Candidate, Result.candidate_id == Candidate.id
    ).filter(
        Result.candidate_id == candidate_id
    ).all()

    # Prepare the response
    result_list = []
    for result, first_name, last_name in results:
        result_info = {
            'candidate_id': result.candidate_id,
            'candidate_name': f'{first_name} {last_name}',
            'vote_type': result.vote_type,
            'vote_count': result.vote_count
        }
        result_list.append(result_info)

    return jsonify(result_list)
