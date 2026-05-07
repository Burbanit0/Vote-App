"""
simulation_advanced.py — Advanced analysis endpoints.

Serves SimulationComparePage (/simulation/compare) tabs:
Bandwagon, Monte Carlo, Multi-winner, Real Elections.

All endpoints use the spatial utility pipeline.
"""
import math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Blueprint, request, jsonify

from app.utils.simulation_voting_utils import run_bandwagon_simulation
from app.utils.simulation_metrics import compare_all_methods_mc
from app.utils.simulation_multiwinner_utils import compare_multiwinner_methods
from app.utils.real_election_data import analyze_real_election, list_elections
from app.routes.simulation_helpers import _parse_candidate_configs, _build_population

simulation_advanced_bp = Blueprint("simulation_advanced", __name__, url_prefix="/simulations")


@simulation_advanced_bp.route("/bandwagon", methods=["POST"])
def bandwagon_route():
    """
    Simulate cascading social influence across N rounds and measure how
    each voting method amplifies or resists bandwagon effects.

    Body: {
        "num_voters": int,
        "candidates": [str, ...] | [dict, ...],
        "num_rounds": int,
        "influence_strength": float,
        "ideology_distribution": str,
        "seed": int | null
    }
    """
    data = request.get_json() or {}
    num_voters         = int(data.get("num_voters", 300))
    num_rounds         = int(data.get("num_rounds", 5))
    influence_strength = float(data.get("influence_strength", 0.3))
    ideology_dist      = data.get("ideology_distribution", "random")
    seed               = data.get("seed")
    raw_candidates     = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    try:
        _, candidates, issues = _build_population(candidate_configs, 0, ideology_dist)
        result = run_bandwagon_simulation(
            num_voters=num_voters,
            candidates=candidates,
            issues=issues,
            num_rounds=num_rounds,
            influence_strength=influence_strength,
            ideology_distribution=ideology_dist,
            seed=int(seed) if seed is not None else None,
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@simulation_advanced_bp.route("/monte-carlo", methods=["POST"])
def monte_carlo_route():
    """
    Run compare_all_methods_mc() N times in parallel and aggregate
    statistical distributions for each voting method.

    Body: {
        "num_runs": int,              // default 100, max 500
        "num_voters": int,            // per run, default 150
        "candidates": [str|dict, ...],
        "ideology_distribution": str
    }
    """
    data           = request.get_json() or {}
    num_runs       = min(int(data.get("num_runs", 100)), 500)
    num_voters     = int(data.get("num_voters", 150))
    ideology_dist  = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    def _single_run(_):
        voters, candidates, issues = _build_population(candidate_configs, num_voters, ideology_dist)
        return compare_all_methods_mc(voters, candidates, issues)

    try:
        run_results = []
        with ThreadPoolExecutor(max_workers=min(4, num_runs)) as executor:
            futures = [executor.submit(_single_run, i) for i in range(num_runs)]
            for f in as_completed(futures):
                run_results.append(f.result())

        method_names = list(run_results[0]["methods"].keys())
        n_candidates = len(candidate_configs)

        winner_counts  = {m: defaultdict(int) for m in method_names}
        regrets        = {m: [] for m in method_names}
        satisfactions  = {m: [] for m in method_names}
        condorcet_hits = {m: 0 for m in method_names}
        condorcet_runs = {m: 0 for m in method_names}
        agreement_counts: dict = defaultdict(int)
        agreement_total: dict = defaultdict(int)
        condorcet_exists = 0

        for run in run_results:
            if run["condorcet_winner"]:
                condorcet_exists += 1
            run_winners = {}
            for m, d in run["methods"].items():
                w = d.get("winner")
                run_winners[m] = w
                if w:
                    winner_counts[m][w] += 1
                r = d.get("bayesian_regret")
                if r is not None:
                    regrets[m].append(r)
                s = d.get("majority_satisfaction")
                if s is not None:
                    satisfactions[m].append(s)
                cc = d.get("condorcet_consistent")
                if cc is not None:
                    condorcet_runs[m] += 1
                    if cc:
                        condorcet_hits[m] += 1
            for i, m1 in enumerate(method_names):
                for m2 in method_names[i + 1:]:
                    key = f"{m1}|{m2}"
                    agreement_total[key] += 1
                    if run_winners.get(m1) and run_winners[m1] == run_winners.get(m2):
                        agreement_counts[key] += 1

        def _ci95(values):
            if len(values) < 2:
                return [None, None]
            mu = sum(values) / len(values)
            var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
            margin = 1.96 * math.sqrt(var) / math.sqrt(len(values))
            return [round(mu - margin, 6), round(mu + margin, 6)]

        def _entropy(dist, n_cand):
            e = -sum(p * math.log2(p) for p in dist.values() if p > 0)
            max_e = math.log2(n_cand) if n_cand > 1 else 1.0
            return round(e / max_e if max_e > 0 else 0.0, 4)

        methods_stats = {}
        for m in method_names:
            dist = {c: round(cnt / num_runs, 4) for c, cnt in winner_counts[m].items()}
            most_common = max(winner_counts[m], key=winner_counts[m].get) if winner_counts[m] else None
            regs = regrets[m]
            sats = satisfactions[m]
            reg_mean = round(sum(regs) / len(regs), 6) if regs else None
            reg_std = round(
                math.sqrt(sum((v - reg_mean) ** 2 for v in regs) / max(1, len(regs) - 1)), 6
            ) if regs and len(regs) > 1 and reg_mean is not None else None
            methods_stats[m] = {
                "winner_distribution":         dist,
                "most_common_winner":          most_common,
                "winner_stability":            _entropy(dist, n_candidates),
                "bayesian_regret_mean":        reg_mean,
                "bayesian_regret_std":         reg_std,
                "bayesian_regret_ci_95":       _ci95(regs),
                "majority_satisfaction_mean":  round(sum(sats) / len(sats), 4) if sats else None,
                "majority_satisfaction_ci_95": _ci95(sats),
                "condorcet_compliance_rate":   (
                    round(condorcet_hits[m] / condorcet_runs[m], 4)
                    if condorcet_runs[m] > 0 else None
                ),
            }

        inter_agreement = {
            key: round(agreement_counts[key] / agreement_total[key], 4)
            for key in agreement_total if agreement_total[key] > 0
        }

        return jsonify({
            "num_runs":                     num_runs,
            "num_voters_per_run":           num_voters,
            "config": {
                "candidates":            [cfg["name"] for cfg in candidate_configs],
                "ideology_distribution": ideology_dist,
            },
            "methods":                      methods_stats,
            "condorcet_winner_exists_rate": round(condorcet_exists / num_runs, 4),
            "inter_method_agreement":       inter_agreement,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@simulation_advanced_bp.route("/multiwinner", methods=["POST"])
def multiwinner_route():
    """
    Compare proportional multi-winner methods on a given vote distribution.

    Body: {
        "party_votes": {"Party A": 40, "Party B": 25, ...},
        "num_seats": int,
        "mode": "proportional" | "stv"
    }
    """
    data        = request.get_json() or {}
    party_votes = data.get("party_votes", {})
    num_seats   = int(data.get("num_seats", 10))
    mode        = data.get("mode", "proportional")

    if not party_votes:
        return jsonify({"error": "party_votes is required"}), 400
    if num_seats < 1:
        return jsonify({"error": "num_seats must be >= 1"}), 400

    try:
        voter_rankings = None
        if mode == "stv":
            import random as _rng
            parties   = list(party_votes.keys())
            total_v   = sum(float(v) for v in party_votes.values())
            weights   = [float(party_votes[p]) / total_v for p in parties]
            voter_rankings = []
            for _ in range(500):
                first = _rng.choices(parties, weights=weights, k=1)[0]
                rest  = _rng.sample([p for p in parties if p != first], len(parties) - 1)
                voter_rankings.append([first] + rest)

        result = compare_multiwinner_methods(
            party_votes={p: float(v) for p, v in party_votes.items()},
            num_seats=num_seats,
            voter_rankings=voter_rankings,
        )
        result["party_votes"] = {p: float(v) for p, v in party_votes.items()}
        result["num_seats"]   = num_seats
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@simulation_advanced_bp.route("/real-elections", methods=["GET"])
def real_elections_list():
    """Return the list of available historical elections."""
    return jsonify(list_elections()), 200


@simulation_advanced_bp.route("/real-election", methods=["POST"])
def real_election_analyze():
    """
    Analyse a real historical election under every voting method.

    Body: { "election_name": str, "num_voters": int }
    """
    data          = request.get_json() or {}
    election_name = data.get("election_name", "")
    num_voters    = int(data.get("num_voters", 1000))

    if not election_name:
        return jsonify({"error": "election_name is required"}), 400

    try:
        result = analyze_real_election(election_name, num_voters)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
