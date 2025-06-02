from flask import Blueprint, request, jsonify
from app.utils.simulation_utils import simulate_votes, get_condorcet_winner, get_two_round_winner
from app.simulation.population_simulation import simulate_population, generate_coord_candidates, assign_voters_to_candidates

bp = Blueprint('simulations', __name__, url_prefix='/simulations')

@bp.route('/', methods=['POST'])
def simulate_votes_route():
    data = request.get_json()
    num_voters = data.get('num_voters')
    num_candidates = data.get('num_candidates')

    if num_voters is None or num_candidates is None:
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        num_voters = int(num_voters)
        num_candidates = int(num_candidates)
    except ValueError:
        return jsonify({'error': 'Parameters must be integers'}), 400

    if num_voters <= 0 or num_candidates <= 0:
        return jsonify({'error': 'Parameters must be positive integers'}), 400

    votes = simulate_votes(num_voters, num_candidates)
    winner_condorcet = get_condorcet_winner(votes)
    winner_two_round = get_two_round_winner(votes)

    response = {
        'votes': votes,
        'condorcet_winner': winner_condorcet,
        'two_round_winner': winner_two_round,
    }

    return jsonify(response), 200

@bp.route('/simulate_voters', methods=['POST'])
def simulate_voters_repartitions():
    data = request.get_json()
    num_voters = data.get('num_voters')
    average_age = data.get('avg_age')

    if num_voters is None or average_age is None:
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        num_voters = int(num_voters)
        average_age = int(average_age)
    except ValueError:
        return jsonify({'error': 'Parameters must be integers'}), 400

    if num_voters <= 0 or average_age <= 0:
        return jsonify({'error': 'Parameters must be positive integers'}), 400
    
    coords = simulate_population(num_voters, average_age)
    
    response = {
        'coord': coords
    }

    return jsonify(response), 200

@bp.route('/simulate_candidates', methods=['POST'])
def simulate_candidates_repartitions():
    data = request.get_json()
    num_candidates = data.get('num_candidates')

    if num_candidates is None:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        num_candidates = int(num_candidates)
    except ValueError:
        return jsonify({'error':'Parameter must be integer'}), 400
    
    if num_candidates <= 0:
        return jsonify({'error': 'Parameter must be positive integer'}), 400
    
    coords = generate_coord_candidates(num_candidates)

    response = {
        'coord': coords
    }

    return jsonify(response), 200

@bp.route('/get_closest_candidate', methods=['POST'])
def get_closest_candidates():
    data = request.get_json()
    candidates = data.get(candidates)
    voters = data.get(voters)

    if voters is None or candidates is None:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    result = assign_voters_to_candidates(voters, candidates)

    response = {
        'result' : result 
    }

    return jsonify(response), 200