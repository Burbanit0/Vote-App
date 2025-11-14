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
)
from app.utils.simulation_score_utils import (
    get_mean_median_hybrid_winner,
    get_median_voting_winner,
    get_score_distribution_analysis,
    get_simple_score_winner,
    get_star_voting_winner,
    get_variance_based_winner,
)


simulation_bp = Blueprint("simulations", __name__, url_prefix="/simulations")


@simulation_bp.route("/", methods=["POST"])
def simulate_votes_route():
    data = request.get_json()
    form_data = data.get("formData")
    population_size = form_data.get("populationSize")
    candidates = form_data.get("candidates")
    demographics = form_data.get("demographics")
    turnout_rate = form_data.get("turnoutRate")
    influence_weights = form_data.get("influenceWeights")
    simulation_type = form_data.get("simulationType")

    if form_data is None:
        return jsonify({"error": "Missing required parameters"}), 400

    if "votes" in simulation_type:
        voters, votes, tally = simulate_voters(
            population_size, candidates, demographics, influence_weights, turnout_rate
        )
    if "ranked" in simulation_type:
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

    if "scores" in simulation_type:
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
