from flask import Blueprint, request, jsonify
from app.utils.simulation_utils import simulate_votes, get_condorcet_winner, get_two_round_winner

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