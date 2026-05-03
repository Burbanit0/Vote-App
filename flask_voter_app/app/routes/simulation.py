from flask import Blueprint, request, jsonify
from app.utils.simul import (
    simulate_voters,
    simulate_score_voters,
    simulate_ranked_voters,
)
from app.utils.simulation_ranked_utils import (
    get_condorcet_winner,
    get_two_round_winner,
    get_borda_winner,
    get_plurality_winner,
    get_approval_winner,
    get_irv_winner,
    get_coombs_winner,
    get_score_winner,
    get_kemeny_young_winner,
    get_bucklin_winner,
    get_minimax_winner,
    get_schulze_winner,
)
from app.simulation.population_simulation import assign_voters_to_candidates
from app.utils.simulation_voting_utils import (
    calculate_utility,
    create_voter,
    create_candidate,
    compute_strategic_plurality_vote,
)
from app.utils.simulation_score_utils import (
    get_mean_median_hybrid_winner,
    get_median_voting_winner,
    get_score_distribution_analysis,
    get_simple_score_winner,
    get_star_voting_winner,
    get_variance_based_winner,
)
from app.utils.simulation_metrics import compare_all_methods, get_condorcet_matrix


simulation_bp = Blueprint("simulations", __name__, url_prefix="/simulations")


@simulation_bp.route("/", methods=["POST"])
def simulate_votes_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    form_data = data.get("formData")
    if form_data is None:
        return jsonify({"error": "Missing required parameters"}), 400

    population_size = form_data.get("populationSize")
    candidates = form_data.get("candidates")
    demographics = form_data.get("demographics")
    turnout_rate = form_data.get("turnoutRate")
    influence_weights = form_data.get("influenceWeights")
    simulation_type = form_data.get("simulationType")

    if "votes" in simulation_type:
        voters, votes, tally = simulate_voters(
            population_size, candidates, demographics, influence_weights, turnout_rate
        )
    elif "ranked" in simulation_type:
        voters_r, rankings, first_choice_tally = simulate_ranked_voters(
            population_size, candidates, demographics, influence_weights, turnout_rate
        )
        condorcet_winner = get_condorcet_winner(rankings)
        two_round_winner = get_two_round_winner(rankings)
        borda_winner = get_borda_winner(rankings)
        plurality_winner = get_plurality_winner(rankings)
        approval_winner = get_approval_winner(rankings)
        irv_winner = get_irv_winner(rankings)
        coombs_winner = get_coombs_winner(rankings)
        score_winner = get_score_winner(rankings)
        kemeny_young_winner = get_kemeny_young_winner(rankings)
        bucklin_winner = get_bucklin_winner(rankings)
        minimax_winner = get_minimax_winner(rankings)
        schulze_winner = get_schulze_winner(rankings)

    elif "scores" in simulation_type:
        voters_n, all_scores, avg_scores = simulate_score_voters(
            population_size, candidates, demographics, influence_weights, turnout_rate
        )
        mean_median_hybrid_winner = get_mean_median_hybrid_winner(all_scores)
        median_voting_winner = get_median_voting_winner(all_scores)
        score_distribution_analysis = get_score_distribution_analysis(all_scores)
        simple_score_winner = get_simple_score_winner(all_scores)
        star_voting_winner = get_star_voting_winner(all_scores)
        variance_based_winner = get_variance_based_winner(all_scores)

    response = {
        "simulation_type": simulation_type,
        "metadata": {
            "population_size": population_size,
            "candidates": candidates,
            "turnout_rate": turnout_rate,
            "demographics": demographics,
            "influence_weights": influence_weights,
        },
    }

    # Add simulation-specific data
    if "votes" in simulation_type:
        response.update(
            {
                "votes": [
                    {"voter_id": voter["id"], "preference": voter["preference"]}
                    for voter in voters
                    if voter["turnout"]
                ],
                "tally": tally,
                "voters_sample": [
                    {k: v for k, v in voter.items() if k != "scores" and k != "ranking"}
                    for voter in voters
                ],
            }
        )

    if "ranked" in simulation_type:
        response.update(
            {
                "rankings": [
                    {"voter_id": voter["id"], "ranking": voter["ranking"]}
                    for voter in voters_r
                    if voter["turnout"]
                ],
                "first_choice_tally": first_choice_tally,
                "voters_sample": [
                    {
                        k: v
                        for k, v in voter.items()
                        if k != "scores" and k != "preference"
                    }
                    for voter in voters_r
                ],
            }
        )

    if "scores" in simulation_type:
        response.update(
            {
                "all_scores": [
                    {"voter_id": voter["id"], "scores": voter["scores"]}
                    for voter in voters_n
                    if voter["turnout"]
                ],
                "avg_scores": avg_scores,
                "voters_sample": [
                    {
                        k: v
                        for k, v in voter.items()
                        if k != "preference" and k != "ranking"
                    }
                    for voter in voters_n
                ],
            }
        )

    # Add common analysis results if available
    if "condorcet_winner" in locals():
        response["condorcet_winner"] = condorcet_winner

    if "two_round_winner" in locals():
        response["two_round_winner"] = two_round_winner

    if "borda_winner" in locals():
        response["borda_winner"] = borda_winner

    if "plurality_winner" in locals():
        response["plurality_winner"] = plurality_winner

    if "approval_winner" in locals():
        response["approval_winner"] = approval_winner

    if "irv_winner" in locals():
        response["irv_winner"] = irv_winner

    if "coombs_winner" in locals():
        response["coombs_winner"] = coombs_winner

    if "score_winner" in locals():
        response["score_winner"] = score_winner

    if "kemeny_young_winner" in locals():
        response["kemeny_young_winner"] = kemeny_young_winner

    if "bucklin_winner" in locals():
        response["bucklin_winner"] = bucklin_winner

    if "minimax_winner" in locals():
        response["minimax_winner"] = minimax_winner

    if "schulze_winner" in locals():
        response["schulze_winner"] = schulze_winner

    if "mean_median_hybrid_winner" in locals():
        response["mean_median_hybrid_winner"] = mean_median_hybrid_winner

    if "median_voting_winner" in locals():
        response["median_voting_winner"] = median_voting_winner

    if "score_distribution_analysis" in locals():
        response["score_distribution_analysis"] = score_distribution_analysis

    if "simple_score_winner" in locals():
        response["simple_score_winner"] = simple_score_winner

    if "star_voting_winner" in locals():
        response["star_voting_winner"] = star_voting_winner

    if "variance_based_winner" in locals():
        response["variance_based_winner"] = variance_based_winner

    return jsonify(response), 200


@simulation_bp.route("/simulate_voters", methods=["POST"])
def simulate_voters_repartitions():
    """
    Simulate voters with their profiles
    Expected JSON payload:
    {
        "num_voters": int,  # Number of voters to generate
    }
    Returns:
    {
        "voters":
        [
            {
                "id": int
                "age": int,
                "education": str,
                "gender": str,
                "income": str,
                "region": str,
                 "employment_status": str,
                "family_status": str,
                "ethnicity_immigration": str,
                "religion": str,
                "issue_priorities": {
                    "agriculture": float,
                    "defense": float,
                    "economy": float,
                    "education": float,
                    "environment": float,
                    "gender_equality": float,
                    "healthcare": float,
                    "jobs": float,
                    "public_transport": float,
                    "social_welfare": float,
                    "taxes": float
                },
                "likelihood_to_vote": float,
                "mood": float,
                "party_loyalty": float,
                "political_lean": float,
                "preferred_party": str
            },
            ...
        ]
    }
    """
    data = request.json
    num_voters = data.get("num_voters", 1000)
    issues = [
        "economy",
        "environment",
        "healthcare",
        "education",
        "taxes",
        "social_welfare",
        "agriculture",
        "public_transport",
        "defense",
        "gender_equality",
        "pensions",
        "climate_change",
        "housing",
        "immigration",
        "crime_safety",
        "technology_innovation",
        "minimum_wage",
        "business_regulation",
        "jobs",
        "infrastructure",
    ]

    voters = [create_voter(issues, i) for i in range(num_voters)]
    return jsonify({"voters": voters})


@simulation_bp.route("/simulate_candidates", methods=["POST"])
def simulate_candidates_repartitions():
    """
    Simulate political candidates with their profiles
    Expected JSON payload:
    {
        "num_candidates": int,  # Number of candidates to generate (default: 4)
        "issues": list,         # List of policy issues
        "parties": list         # Optional: specific parties to include
    }
    Returns:
    {
        "candidates": [
            {
                "id": int,
                "name": str,
                "party": str,
                "party_lean": float,
                "policies": dict,
                "charisma": float,
                "scandals": int,
                "campaign_funds": float,
                "experience": int,
                "popularity": float
            },
            ...
        ]
    }
    """
    data = request.json
    num_candidates = data.get("num_candidates", 4)
    issues = data.get(
        "issues",
        [
            "economy",
            "environment",
            "healthcare",
            "education",
            "taxes",
            "social_welfare",
            "agriculture",
            "public_transport",
            "defense",
            "gender_equality",
            "pensions",
            "climate_change",
            "housing",
            "immigration",
            "crime_safety",
            "technology_innovation",
            "minimum_wage",
            "business_regulation",
            "jobs",
            "infrastructure",
        ],
    )

    # Default parties if not specified
    default_parties = ["Green", "Conservative", "Liberal", "Independent"]
    parties = data.get("parties", default_parties)

    # If we need more candidates than parties, we'll repeat parties
    if num_candidates > len(parties):
        parties *= num_candidates // len(parties) + 1
    parties = parties[:num_candidates]

    candidates = []
    for i in range(num_candidates):
        party = parties[i]
        name = f"Candidate {i+1} ({party})"
        candidates.append(create_candidate(issues, i, name, party))

    return jsonify(
        {
            "success": True,
            "candidates": candidates,
            "message": f"Successfully generated {num_candidates} candidates",
        }
    )


@simulation_bp.route("/get_closest_candidate", methods=["POST"])
def get_closest_candidates():
    data = request.get_json()
    candidates = data.get("candidates")
    voters = data.get("voters")

    if voters is None or candidates is None:
        return jsonify({"error": "Missing required parameters"}), 400

    result = assign_voters_to_candidates(voters, candidates)

    response = {"result": result}

    return jsonify(response), 200


@simulation_bp.route("/simulate_utility", methods=["POST"])
def simulate_utility():
    """
    Simulate utility scores between voters and candidates.
    Expected JSON payload:
    {
        "num_voters": int,      # Number of voters to generate (default: 100)
        "num_candidates": int,  # Number of candidates to generate (default: 4)
        "issues": list,         # List of policy issues
        "parties": list         # Optional: specific parties to include
    }
    Returns:
    {
        "voters": [...],
        "candidates": [...],
        "utility_results": [...]
    }
    """
    try:
        data = request.json
        voters = data.get("voters")
        candidates = data.get("candidates")
        issues = data.get(
            "issues",
            [
                "economy",
                "environment",
                "healthcare",
                "education",
                "taxes",
                "social_welfare",
                "agriculture",
                "public_transport",
                "defense",
                "gender_equality",
                "pensions",
                "climate_change",
                "housing",
                "immigration",
                "crime_safety",
                "technology_innovation",
                "minimum_wage",
                "business_regulation",
                "jobs",
                "infrastructure",
            ],
        )

        # Calculate utility for all voter-candidate pairs
        utility_results = []
        for voter in voters:
            for candidate in candidates:
                utility_results.append(calculate_utility(voter, candidate, issues))

        return jsonify({"success": True, "utility_results": utility_results})

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to simulate utility scores",
                }
            ),
            500,
        )


@simulation_bp.route("/calculate_utility", methods=["POST"])
def calculate_single_utility():
    """
    Calculate utility for a specific voter-candidate pair.
    Expected JSON payload:
    {
        "voter": {...},
        "candidate": {...},
        "issues": list
    }
    Returns:
    {
        "utility": float,
        "will_vote": bool,
        "breakdown": {...}
    }
    """
    try:
        data = request.json
        voter = data.get("voter")
        candidate = data.get("candidate")
        issues = data.get(
            "issues",
            [
                "economy",
                "environment",
                "healthcare",
                "education",
                "taxes",
                "social_welfare",
                "agriculture",
                "public_transport",
                "defense",
                "gender_equality",
                "pensions",
                "climate_change",
                "housing",
                "immigration",
                "crime_safety",
                "technology_innovation",
                "minimum_wage",
                "business_regulation",
                "jobs",
                "infrastructure",
            ],
        )

        if not voter or not candidate:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Voter and candidate data are required",
                        "message": "Missing voter or candidate data",
                    }
                ),
                400,
            )

        result = calculate_utility(voter, candidate, issues)

        return jsonify(
            {
                "success": True,
                "result": result,
                "message": "Utility calculated successfully",
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to calculate utility",
                }
            ),
            500,
        )


@simulation_bp.route("/get_utility_matrix", methods=["POST"])
def get_utility_matrix():
    """
    Get utility matrix for a set of voters and candidates.
    Expected JSON payload:
    {
        "voters": [...],
        "candidates": [...],
        "issues": list
    }
    Returns:
    {
        "matrix": {
            "voter_ids": [...],
            "candidate_ids": [...],
            "values": [[...], [...]]  # 2D array of utility scores
        },
        "stats": {
            "average_utility": float,
            "vote_shares": {...}
        }
    }
    """
    try:
        data = request.json
        voters = data.get("voters", [])
        candidates = data.get("candidates", [])
        issues = data.get(
            "issues",
            [
                "economy",
                "environment",
                "healthcare",
                "education",
                "taxes",
                "social_welfare",
                "agriculture",
                "public_transport",
                "defense",
                "gender_equality",
                "pensions",
                "climate_change",
                "housing",
                "immigration",
                "crime_safety",
                "technology_innovation",
                "minimum_wage",
                "business_regulation",
                "jobs",
                "infrastructure",
            ],
        )

        if not voters or not candidates:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Voters and candidates are required",
                        "message": "Missing voters or candidates data",
                    }
                ),
                400,
            )

        # Calculate utility matrix
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

        # Calculate stats
        average_utility = total_utility / total_pairs if total_pairs > 0 else 0
        vote_shares = {
            candidate["id"]: count / len(voters)
            for candidate, count in zip(candidates, vote_counts.values())
        }

        return jsonify(
            {
                "success": True,
                "matrix": {
                    "voter_ids": [voter["id"] for voter in voters],
                    "candidate_ids": [candidate["id"] for candidate in candidates],
                    "values": matrix,
                },
                "stats": {
                    "average_utility": round(average_utility, 4),
                    "vote_shares": {
                        candidate["id"]: {
                            "name": candidate["name"],
                            "share": round(vote_shares[candidate["id"]], 4),
                        }
                        for candidate in candidates
                    },
                },
                "message": f"""Utility matrix calculated for
                    {len(voters)} voters and {len(candidates)} candidates""",
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to calculate utility matrix",
                }
            ),
            500,
        )


@simulation_bp.route("/get_voter_segments", methods=["POST"])
def get_voter_segments():
    """
    Get utility analysis by voter segments.
    Expected JSON payload:
    {
        "voters": [...],
        "candidates": [...],
        "issues": list,
        "segments": ["young_female", "old_male", "high_edu", "low_income",
                     "urban", "rural"]
    }
    Returns:
    {
        "segments": {
            "segment_name": {
                "count": int,
                "average_utility": float,
                "top_candidate": {...},
                "utility_distribution": [...]
            }
        }
    }
    """
    try:
        data = request.json
        voters = data.get("voters", [])
        candidates = data.get("candidates", [])
        issues = data.get(
            "issues",
            [
                "economy",
                "environment",
                "healthcare",
                "education",
                "taxes",
                "social_welfare",
                "agriculture",
                "public_transport",
                "defense",
                "gender_equality",
                "pensions",
                "climate_change",
                "housing",
                "immigration",
                "crime_safety",
                "technology_innovation",
                "minimum_wage",
                "business_regulation",
                "jobs",
                "infrastructure",
            ],
        )
        segment_types = data.get(
            "segments",
            ["young_female", "old_male", "high_edu", "low_income", "urban", "rural"],
        )

        if not voters or not candidates:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Voters and candidates are required",
                        "message": "Missing voters or candidates data",
                    }
                ),
                400,
            )

        # Define segment tests
        segment_definitions = {
            "young_female": {
                "test": lambda v: v["age"] <= 30 and v["gender"] == "female",
                "label": "Jeunes femmes (18-30)",
            },
            "old_male": {
                "test": lambda v: v["age"] > 60 and v["gender"] == "male",
                "label": "Hommes âgés (60+)",
            },
            "high_edu": {
                "test": lambda v: v["education"] in ["master", "phd"],
                "label": "Éducation élevée",
            },
            "low_income": {
                "test": lambda v: v["income"] == "low",
                "label": "Faible revenu",
            },
            "urban": {"test": lambda v: v["region"] == "urban", "label": "Urbains"},
            "rural": {"test": lambda v: v["region"] == "rural", "label": "Ruraux"},
        }

        # Filter segments
        segment_definitions = {
            k: v for k, v in segment_definitions.items() if k in segment_types
        }

        # Calculate utilities for all pairs
        utility_results = []
        for voter in voters:
            for candidate in candidates:
                utility_results.append(calculate_utility(voter, candidate, issues))

        # Prepare segment analysis
        segments = {}
        for seg_key, seg_def in segment_definitions.items():
            segment_voters = [v for v in voters if seg_def["test"](v)]
            if not segment_voters:
                continue

            segment_utilities = []
            for voter in segment_voters:
                voter_utilities = [
                    r for r in utility_results if r["voter_id"] == voter["id"]
                ]
                if voter_utilities:
                    # Find max utility for this voter
                    max_utility = max(voter_utilities, key=lambda x: x["utility"])
                    segment_utilities.append(max_utility)

            if not segment_utilities:
                continue

            # Calculate segment stats
            avg_utility = sum(u["utility"] for u in segment_utilities) / len(
                segment_utilities
            )

            # Find top candidate for this segment
            candidate_votes = {}
            for u in segment_utilities:
                candidate_id = u["candidate_id"]
                candidate_votes[candidate_id] = candidate_votes.get(candidate_id, 0) + 1

            if candidate_votes:
                top_candidate_id = max(candidate_votes.items(), key=lambda x: x[1])[0]
                top_candidate = next(
                    (c for c in candidates if c["id"] == top_candidate_id), None
                )
                top_utility = next(
                    (
                        u["utility"]
                        for u in segment_utilities
                        if u["candidate_id"] == top_candidate_id
                    ),
                    0,
                )
            else:
                top_candidate = None
                top_utility = 0

            segments[seg_key] = {
                "label": seg_def["label"],
                "count": len(segment_voters),
                "average_utility": round(avg_utility, 4),
                "top_candidate": (
                    {
                        "id": top_candidate["id"] if top_candidate else None,
                        "name": top_candidate["name"] if top_candidate else "None",
                        "party": top_candidate["party"] if (top_candidate) else "None",
                        "utility": round(top_utility, 4) if top_candidate else 0,
                    }
                    if top_candidate
                    else None
                ),
                "utility_distribution": [
                    round(u["utility"], 4) for u in segment_utilities
                ],
            }

        return jsonify(
            {
                "success": True,
                "segments": segments,
                "message": f"""Segment analysis completed
                        for {len(segments)} segments""",
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to calculate voter segments",
                }
            ),
            500,
        )


# ── Shared helpers ────────────────────────────────────────────────────────

_DEFAULT_ISSUES = [
    "economy", "environment", "healthcare", "education", "taxes",
    "social_welfare", "agriculture", "public_transport", "defense",
    "gender_equality", "pensions", "climate_change", "housing",
    "immigration", "crime_safety", "technology_innovation",
    "minimum_wage", "business_regulation", "jobs", "infrastructure",
]

_PARTY_CYCLE = ["Green", "Conservative", "Liberal", "Independent"]


def _parse_candidate_configs(raw: list) -> list:
    """
    Normalise the candidates field from the request body.

    Accepts two formats:
      - List of strings:  ["Alice", "Bob"]
      - List of dicts:    [{"name": "Alice", "party": "Liberal",
                            "ideology_position": 0.3}, ...]

    Always returns a list of dicts with at least {"name", "party"} keys.
    """
    configs = []
    for i, item in enumerate(raw):
        if isinstance(item, str):
            configs.append({
                "name": item,
                "party": _PARTY_CYCLE[i % len(_PARTY_CYCLE)],
                "ideology_position": None,
            })
        else:
            configs.append({
                "name": item.get("name", f"Candidate {i + 1}"),
                "party": item.get("party", _PARTY_CYCLE[i % len(_PARTY_CYCLE)]),
                "ideology_position": item.get("ideology_position"),
            })
    return configs


def _build_population(
    candidate_configs: list,
    num_voters: int,
    ideology_distribution: str = "random",
):
    """
    Create voters and candidates.

    candidate_configs — output of _parse_candidate_configs() (list of dicts
    with name, party, ideology_position keys).
    """
    issues = _DEFAULT_ISSUES
    candidates = [
        create_candidate(
            issues,
            i,
            cfg["name"],
            cfg["party"],
            ideology_position=cfg.get("ideology_position"),
        )
        for i, cfg in enumerate(candidate_configs)
    ]
    voters = [
        create_voter(issues, i, ideology_distribution=ideology_distribution)
        for i in range(num_voters)
    ]
    return voters, candidates, issues


# ── /simulations/compare ─────────────────────────────────────────────────

@simulation_bp.route("/compare", methods=["POST"])
def compare_methods():
    """
    Run compare_all_methods on a fresh population and return per-method metrics.

    Body: {
        "num_voters": int,
        "ideology_distribution": str,          // optional, default "random"
        "candidates": [str, ...] | [dict, ...]  // strings or full config dicts
    }
    Candidate dict format: {"name": str, "party": str, "ideology_position": float|null}
    """
    data = request.get_json() or {}
    num_voters = int(data.get("num_voters", 500))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    try:
        voters, candidates, issues = _build_population(
            candidate_configs, num_voters, ideology_distribution
        )
        result = compare_all_methods(voters, candidates, issues)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /simulations/strategic-impact ────────────────────────────────────────

@simulation_bp.route("/strategic-impact", methods=["POST"])
def strategic_impact():
    """
    Measure how bayesian_regret per method changes as the proportion of
    strategic voters increases.  Non-plurality methods always use sincere
    rankings, so only plurality degrades — this empirically demonstrates
    which methods resist strategic manipulation.

    Body: {
        "num_voters": int,
        "ideology_distribution": str,           // optional, default "random"
        "candidates": [str, ...] | [dict, ...], // strings or full config dicts
        "strategic_percentages": [0, 10, 20, 30, 40, 50]
    }
    """
    data = request.get_json() or {}
    num_voters = int(data.get("num_voters", 500))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])
    strategic_percentages = data.get("strategic_percentages", [0, 10, 20, 30, 40, 50])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    try:
        voters, candidates, issues = _build_population(
            candidate_configs, num_voters, ideology_distribution
        )

        # Pre-compute utilities once — reused across all strategic levels.
        utilities = {}
        for voter in voters:
            utilities[voter["id"]] = {
                c["name"]: calculate_utility(voter, c, issues)["utility"]
                for c in candidates
            }

        # Sincere baseline from compare_all_methods (covers all non-plurality methods).
        sincere = compare_all_methods(voters, candidates, issues)

        # Sort voters by strategic propensity so we can apply a precise %.
        sorted_voters = sorted(
            voters, key=lambda v: -v.get("strategic_propensity", 0)
        )

        results = []
        for pct in strategic_percentages:
            n_strategic = int(len(voters) * pct / 100)

            # Sincere poll standings (first choices by utility).
            poll_standings = {}
            for voter in voters:
                u = utilities[voter["id"]]
                first_choice = max(u, key=u.get)
                poll_standings[first_choice] = poll_standings.get(first_choice, 0) + 1

            # Plurality election with strategic voters.
            plurality_votes = []
            for i, voter in enumerate(sorted_voters):
                u = utilities[voter["id"]]
                if i < n_strategic:
                    choice = compute_strategic_plurality_vote(voter, candidates, issues, poll_standings)
                else:
                    choice = max(u, key=u.get)
                plurality_votes.append([choice] if choice else list(u.keys()))

            plurality_winner = get_plurality_winner(plurality_votes)

            # Bayesian regret for strategic plurality result.
            if plurality_winner:
                total = sum(
                    max(utilities[v["id"]].values())
                    - utilities[v["id"]].get(plurality_winner, 0)
                    for v in voters
                )
                plurality_regret = round(total / len(voters), 6)
            else:
                plurality_regret = None

            # Build per-method regret: plurality uses the strategic result,
            # all other methods keep the sincere result.
            methods_regret = {
                method: (
                    plurality_regret
                    if method == "plurality"
                    else method_data["bayesian_regret"]
                )
                for method, method_data in sincere["methods"].items()
            }

            results.append({"strategic_pct": pct, "methods": methods_regret})

        return jsonify({"results": results}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /simulations/condorcet-matrix ────────────────────────────────────────

@simulation_bp.route("/condorcet-matrix", methods=["POST"])
def condorcet_matrix_route():
    """
    Build the full pairwise duel matrix for a fresh population.

    Body: {
        "num_voters": int,
        "ideology_distribution": str,           // optional, default "random"
        "candidates": [str, ...] | [dict, ...]  // strings or full config dicts
    }
    """
    data = request.get_json() or {}
    num_voters = int(data.get("num_voters", 500))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    try:
        voters, candidates, issues = _build_population(
            candidate_configs, num_voters, ideology_distribution
        )
        result = get_condorcet_matrix(voters, candidates, issues)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /simulations/sensitivity ──────────────────────────────────────────────

@simulation_bp.route("/sensitivity", methods=["POST"])
def sensitivity_analysis():
    """
    Vary one parameter and observe how winners and Bayesian regret change
    across all voting methods.

    Body: {
        "base_config": {
            "num_voters": int,
            "candidates": [str|dict, ...],
            "ideology_distribution": str
        },
        "variable": "ideology_distribution" | "num_voters" | "strategic_pct",
        "values":   [value, ...]
    }

    Returns:
        {
            "variable": str,
            "values": [...],
            "results": [
                {
                    "value": ...,
                    "condorcet_winner": str | None,
                    "winners_by_method": {method: str|None, ...},
                    "regret_by_method":  {method: float|None, ...}
                }, ...
            ]
        }
    """
    data = request.get_json() or {}
    base = data.get("base_config", {})
    variable = data.get("variable", "ideology_distribution")
    values = data.get("values", [])

    if not values:
        return jsonify({"error": "No values provided"}), 400

    base_num_voters = int(base.get("num_voters", 500))
    base_ideology = base.get("ideology_distribution", "random")
    raw_candidates = base.get("candidates", ["Alice", "Bob", "Charlie"])
    candidate_configs = _parse_candidate_configs(raw_candidates)

    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    results = []

    for value in values:
        try:
            # Determine this run's parameters.
            if variable == "ideology_distribution":
                num_voters = base_num_voters
                ideology = str(value)
            elif variable == "num_voters":
                num_voters = max(10, int(value))
                ideology = base_ideology
            else:  # strategic_pct — population params unchanged
                num_voters = base_num_voters
                ideology = base_ideology

            voters, candidates, issues = _build_population(
                candidate_configs, num_voters, ideology
            )

            comparison = compare_all_methods(voters, candidates, issues)
            winners = {m: d["winner"] for m, d in comparison["methods"].items()}
            regrets = {m: d["bayesian_regret"] for m, d in comparison["methods"].items()}

            # For strategic_pct, override plurality with a strategic election.
            if variable == "strategic_pct":
                pct = float(value)

                utilities = {
                    voter["id"]: {
                        c["name"]: calculate_utility(voter, c, issues)["utility"]
                        for c in candidates
                    }
                    for voter in voters
                }

                sorted_voters = sorted(
                    voters, key=lambda v: -v.get("strategic_propensity", 0)
                )
                n_strategic = int(len(voters) * pct / 100)

                poll_standings: dict = {}
                for voter in voters:
                    u = utilities[voter["id"]]
                    top = max(u, key=u.get)
                    poll_standings[top] = poll_standings.get(top, 0) + 1

                plurality_votes = []
                for i, voter in enumerate(sorted_voters):
                    u = utilities[voter["id"]]
                    if i < n_strategic:
                        choice = compute_strategic_plurality_vote(
                            voter, candidates, issues, poll_standings
                        )
                    else:
                        choice = max(u, key=u.get)
                    plurality_votes.append([choice] if choice else list(u.keys()))

                plurality_winner = get_plurality_winner(plurality_votes)
                winners["plurality"] = plurality_winner
                if plurality_winner:
                    total = sum(
                        max(utilities[v["id"]].values())
                        - utilities[v["id"]].get(plurality_winner, 0)
                        for v in voters
                    )
                    regrets["plurality"] = round(total / len(voters), 6)

            results.append({
                "value": value,
                "condorcet_winner": comparison["condorcet_winner"],
                "winners_by_method": winners,
                "regret_by_method": regrets,
            })

        except Exception as exc:
            results.append({
                "value": value,
                "condorcet_winner": None,
                "winners_by_method": {},
                "regret_by_method": {},
                "error": str(exc),
            })

    return jsonify({"variable": variable, "values": values, "results": results}), 200
