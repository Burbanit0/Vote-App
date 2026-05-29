"""
simulation_base.py — Core simulation endpoints.

Serves SimulationPage (/simulation) and its visualisation tabs.
Contains both the legacy influence-weight pipeline and the spatial
population-generation endpoints used by the visualisation components.

LEGACY pipeline (simul.py):
    POST /simulations/                    — form-based vote simulation
    POST /simulations/get_closest_candidate — 2-D spatial assignment

SPATIAL pipeline (simulation_voting_utils.py):
    POST /simulations/simulate_voters
    POST /simulations/simulate_candidates
    POST /simulations/simulate_utility
    POST /simulations/calculate_utility
    POST /simulations/get_utility_matrix
    POST /simulations/get_voter_segments
"""
from flask import Blueprint, request, jsonify, make_response

# Legacy pipeline
from app.utils.simul import simulate_voters, simulate_score_voters, simulate_ranked_voters
from app.simulation.population_simulation import assign_voters_to_candidates

# Shared voting-method functions
from app.utils.simulation_ranked_utils import (
    get_condorcet_winner, get_two_round_winner, get_borda_winner,
    get_plurality_winner, get_approval_winner, get_irv_winner,
    get_coombs_winner, get_positional_score_winner, get_kemeny_young_winner,
    get_bucklin_winner, get_minimax_winner, get_schulze_winner,
)
from app.utils.simulation_score_utils import (
    get_mean_median_hybrid_winner, get_median_voting_winner,
    get_score_distribution_analysis, get_simple_score_winner,
    get_star_voting_winner, get_variance_based_winner,
)

# Spatial pipeline
from app.utils.simulation_voting_utils import calculate_utility, create_voter, create_candidate
from app.constants import DEFAULT_ISSUES

from app.extensions import sim_limiter

simulation_base_bp = Blueprint("simulation_base", __name__, url_prefix="/simulations")


# ── Pure-compute workers (shared by Flask + the FastAPI /api/v2/simulations router)
#
# Phase 4.5.a.5: the framework-agnostic `_*_worker(data) -> (body, status)`
# functions hold all the logic so api_v2/routes/simulations.py can reuse them.
# The Flask routes below are thin delegates kept as a rollback target.


def _simulate_votes_worker(data: dict) -> tuple[dict, int]:
    """Legacy form-based simulation. Returns (body, status); the
    X-Deprecation-Warning header is set by each HTTP adapter from
    body['deprecation_warning']."""
    if not data:
        return {"error": "Missing request body"}, 400
    form_data = data.get("formData")
    if form_data is None:
        return {"error": "Missing required parameters"}, 400

    population_size = form_data.get("populationSize")
    candidates = form_data.get("candidates")
    demographics = form_data.get("demographics")
    turnout_rate = form_data.get("turnoutRate")
    influence_weights = form_data.get("influenceWeights")
    simulation_type = form_data.get("simulationType")

    # Accumulate the method winners here instead of introspecting locals().
    winners: dict = {}

    if "votes" in simulation_type:
        voters, votes, tally = simulate_voters(
            population_size, candidates, demographics, influence_weights, turnout_rate
        )
    elif "ranked" in simulation_type:
        voters_r, rankings, first_choice_tally = simulate_ranked_voters(
            population_size, candidates, demographics, influence_weights, turnout_rate
        )
        winners.update({
            "condorcet_winner":    get_condorcet_winner(rankings),
            "two_round_winner":    get_two_round_winner(rankings),
            "borda_winner":        get_borda_winner(rankings),
            "plurality_winner":    get_plurality_winner(rankings),
            "approval_winner":     get_approval_winner(rankings),
            "irv_winner":          get_irv_winner(rankings),
            "coombs_winner":       get_coombs_winner(rankings),
            "score_winner":        get_positional_score_winner(rankings),
            "kemeny_young_winner": get_kemeny_young_winner(rankings),
            "bucklin_winner":      get_bucklin_winner(rankings),
            "minimax_winner":      get_minimax_winner(rankings),
            "schulze_winner":      get_schulze_winner(rankings),
        })

    elif "scores" in simulation_type:
        voters_n, all_scores, avg_scores = simulate_score_voters(
            population_size, candidates, demographics, influence_weights, turnout_rate
        )
        winners.update({
            "mean_median_hybrid_winner":   get_mean_median_hybrid_winner(all_scores),
            "median_voting_winner":        get_median_voting_winner(all_scores),
            "score_distribution_analysis": get_score_distribution_analysis(all_scores),
            "simple_score_winner":         get_simple_score_winner(all_scores),
            "star_voting_winner":          get_star_voting_winner(all_scores),
            "variance_based_winner":       get_variance_based_winner(all_scores),
        })

    deprecation_warning = (
        "This legacy endpoint will be removed in a future version. "
        "Use /simulations/compare or the spatial pipeline endpoints."
    )
    response = {
        "simulation_type": simulation_type,
        "deprecation_warning": deprecation_warning,
        "metadata": {
            "population_size": population_size,
            "candidates": candidates,
            "turnout_rate": turnout_rate,
            "demographics": demographics,
            "influence_weights": influence_weights,
        },
    }

    if "votes" in simulation_type:
        response.update({
            "votes": [
                {"voter_id": voter["id"], "preference": voter["preference"]}
                for voter in voters if voter["turnout"]
            ],
            "tally": tally,
            "voters_sample": [
                {k: v for k, v in voter.items() if k != "scores" and k != "ranking"}
                for voter in voters
            ],
        })

    if "ranked" in simulation_type:
        response.update({
            "rankings": [
                {"voter_id": voter["id"], "ranking": voter["ranking"]}
                for voter in voters_r if voter["turnout"]
            ],
            "first_choice_tally": first_choice_tally,
            "voters_sample": [
                {k: v for k, v in voter.items() if k != "scores" and k != "preference"}
                for voter in voters_r
            ],
        })

    if "scores" in simulation_type:
        response.update({
            "all_scores": [
                {"voter_id": voter["id"], "scores": voter["scores"]}
                for voter in voters_n if voter["turnout"]
            ],
            "avg_scores": avg_scores,
            "voters_sample": [
                {k: v for k, v in voter.items() if k != "preference" and k != "ranking"}
                for voter in voters_n
            ],
        })

    response.update(winners)
    return response, 200


def _simulate_voters_worker(data: dict) -> tuple[dict, int]:
    num_voters = data.get("num_voters", 1000)
    issues = DEFAULT_ISSUES
    voters = [create_voter(issues, i) for i in range(num_voters)]
    return {"voters": voters}, 200


def _simulate_candidates_worker(data: dict) -> tuple[dict, int]:
    num_candidates = data.get("num_candidates", 4)
    issues = data.get("issues") or DEFAULT_ISSUES
    default_parties = ["Green", "Conservative", "Liberal", "Independent"]
    parties = data.get("parties") or default_parties
    if num_candidates > len(parties):
        parties = parties * (num_candidates // len(parties) + 1)
    parties = parties[:num_candidates]

    candidates = [
        create_candidate(issues, i, f"Candidate {i+1} ({parties[i]})", parties[i])
        for i in range(num_candidates)
    ]
    return {
        "success": True,
        "candidates": candidates,
        "message": f"Successfully generated {num_candidates} candidates",
    }, 200


def _closest_candidate_worker(data: dict) -> tuple[dict, int]:
    candidates = data.get("candidates")
    voters = data.get("voters")
    if not voters or not candidates:
        return {"error": "Missing required parameters"}, 400
    return {"result": assign_voters_to_candidates(voters, candidates)}, 200


def _simulate_utility_worker(data: dict) -> tuple[dict, int]:
    try:
        voters = data.get("voters")
        candidates = data.get("candidates")
        issues = data.get("issues") or DEFAULT_ISSUES
        utility_results = [
            calculate_utility(voter, candidate, issues)
            for voter in voters
            for candidate in candidates
        ]
        return {"success": True, "utility_results": utility_results}, 200
    except Exception as e:
        return {"success": False, "error": str(e),
                "message": "Failed to simulate utility scores"}, 500


def _calculate_utility_worker(data: dict) -> tuple[dict, int]:
    try:
        voter = data.get("voter")
        candidate = data.get("candidate")
        issues = data.get("issues") or DEFAULT_ISSUES
        if not voter or not candidate:
            return {"success": False,
                    "error": "Voter and candidate data are required"}, 400
        result = calculate_utility(voter, candidate, issues)
        return {"success": True, "result": result,
                "message": "Utility calculated successfully"}, 200
    except Exception as e:
        return {"success": False, "error": str(e),
                "message": "Failed to calculate utility"}, 500


def _utility_matrix_worker(data: dict) -> tuple[dict, int]:
    try:
        voters = data.get("voters") or []
        candidates = data.get("candidates") or []
        issues = data.get("issues") or DEFAULT_ISSUES
        if not voters or not candidates:
            return {"success": False,
                    "error": "Voters and candidates are required"}, 400

        matrix = []
        vote_counts = {candidate["id"]: 0 for candidate in candidates}
        total_utility = 0
        total_pairs = 0
        for voter in voters:
            row = []
            for candidate in candidates:
                result = calculate_utility(voter, candidate, issues)
                row.append(result["utility"])
                total_utility += result["utility"]
                total_pairs += 1
                if result["will_vote"]:
                    vote_counts[candidate["id"]] += 1
            matrix.append(row)

        average_utility = total_utility / total_pairs if total_pairs > 0 else 0
        vote_shares = {
            candidate["id"]: count / len(voters)
            for candidate, count in zip(candidates, vote_counts.values())
        }
        return {
            "success": True,
            "matrix": {
                "voter_ids": [v["id"] for v in voters],
                "candidate_ids": [c["id"] for c in candidates],
                "values": matrix,
            },
            "stats": {
                "average_utility": round(average_utility, 4),
                "vote_shares": {
                    c["id"]: {"name": c["name"], "share": round(vote_shares[c["id"]], 4)}
                    for c in candidates
                },
            },
            "message": f"Utility matrix calculated for {len(voters)} voters and {len(candidates)} candidates",
        }, 200
    except Exception as e:
        return {"success": False, "error": str(e),
                "message": "Failed to calculate utility matrix"}, 500


def _voter_segments_worker(data: dict) -> tuple[dict, int]:
    try:
        voters = data.get("voters") or []
        candidates = data.get("candidates") or []
        issues = data.get("issues") or DEFAULT_ISSUES
        segment_types = data.get("segments") or [
            "young_female", "old_male", "high_edu", "low_income", "urban", "rural"]

        if not voters or not candidates:
            return {"success": False,
                    "error": "Voters and candidates are required"}, 400

        segment_definitions = {
            "young_female": {"test": lambda v: v["age"] <= 30 and v["gender"] == "female", "label": "Jeunes femmes (18-30)"},
            "old_male":     {"test": lambda v: v["age"] > 60 and v["gender"] == "male",   "label": "Hommes âgés (60+)"},
            "high_edu":     {"test": lambda v: v["education"] in ["master", "phd"],        "label": "Éducation élevée"},
            "low_income":   {"test": lambda v: v["income"] == "low",                       "label": "Faible revenu"},
            "urban":        {"test": lambda v: v["region"] == "urban",                     "label": "Urbains"},
            "rural":        {"test": lambda v: v["region"] == "rural",                     "label": "Ruraux"},
        }
        segment_definitions = {k: v for k, v in segment_definitions.items() if k in segment_types}

        utility_results = [
            calculate_utility(voter, candidate, issues)
            for voter in voters for candidate in candidates
        ]

        segments = {}
        for seg_key, seg_def in segment_definitions.items():
            segment_voters = [v for v in voters if seg_def["test"](v)]
            if not segment_voters:
                continue
            segment_utilities = []
            for voter in segment_voters:
                voter_utilities = [r for r in utility_results if r["voter_id"] == voter["id"]]
                if voter_utilities:
                    segment_utilities.append(max(voter_utilities, key=lambda x: x["utility"]))
            if not segment_utilities:
                continue
            avg_utility = sum(u["utility"] for u in segment_utilities) / len(segment_utilities)
            candidate_votes = {}
            for u in segment_utilities:
                candidate_votes[u["candidate_id"]] = candidate_votes.get(u["candidate_id"], 0) + 1
            if candidate_votes:
                top_id = max(candidate_votes, key=candidate_votes.get)
                top_candidate = next((c for c in candidates if c["id"] == top_id), None)
                top_utility = next((u["utility"] for u in segment_utilities if u["candidate_id"] == top_id), 0)
            else:
                top_candidate = None
                top_utility = 0
            segments[seg_key] = {
                "label": seg_def["label"],
                "count": len(segment_voters),
                "average_utility": round(avg_utility, 4),
                "top_candidate": {
                    "id": top_candidate["id"],
                    "name": top_candidate["name"],
                    "party": top_candidate["party"],
                    "utility": round(top_utility, 4),
                } if top_candidate else None,
                "utility_distribution": [round(u["utility"], 4) for u in segment_utilities],
            }

        return {"success": True, "segments": segments,
                "message": f"Segment analysis completed for {len(segments)} segments"}, 200
    except Exception as e:
        return {"success": False, "error": str(e),
                "message": "Failed to calculate voter segments"}, 500


# ── Flask routes — thin delegates to the workers above (rollback target) ──────

@simulation_base_bp.route("/", methods=["POST"])
@sim_limiter.limit("30 per minute")
def simulate_votes_route():
    body, status = _simulate_votes_worker(request.get_json(silent=True) or {})
    resp = make_response(jsonify(body), status)
    if "deprecation_warning" in body:
        resp.headers["X-Deprecation-Warning"] = body["deprecation_warning"]
    return resp


@simulation_base_bp.route("/simulate_voters", methods=["POST"])
@sim_limiter.limit("60 per minute")
def simulate_voters_repartitions():
    body, status = _simulate_voters_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/simulate_candidates", methods=["POST"])
@sim_limiter.limit("60 per minute")
def simulate_candidates_repartitions():
    body, status = _simulate_candidates_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/get_closest_candidate", methods=["POST"])
@sim_limiter.limit("60 per minute")
def get_closest_candidates():
    body, status = _closest_candidate_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/simulate_utility", methods=["POST"])
@sim_limiter.limit("30 per minute")
def simulate_utility():
    body, status = _simulate_utility_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/calculate_utility", methods=["POST"])
@sim_limiter.limit("60 per minute")
def calculate_single_utility():
    body, status = _calculate_utility_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/get_utility_matrix", methods=["POST"])
@sim_limiter.limit("30 per minute")
def get_utility_matrix():
    body, status = _utility_matrix_worker(request.get_json(silent=True) or {})
    return jsonify(body), status


@simulation_base_bp.route("/get_voter_segments", methods=["POST"])
@sim_limiter.limit("30 per minute")
def get_voter_segments():
    body, status = _voter_segments_worker(request.get_json(silent=True) or {})
    return jsonify(body), status
