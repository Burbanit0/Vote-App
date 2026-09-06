"""
simulation_advanced.py — Advanced analysis endpoints.

Serves SimulationComparePage (/simulation/compare) tabs:
Bandwagon, Monte Carlo, Multi-winner, Real Elections.

All endpoints use the spatial utility pipeline.

Phase 4.5.a.8: the request logic lives in framework-agnostic `_*_worker`
functions (return `(body, status)`) so the FastAPI sibling
(api/routes/simulations.py) can reuse it. The Flask routes below are thin
delegates kept as a rollback target.
"""
import math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple


import random as _rng2

from api.engine.utils.simulation_voting_utils import run_bandwagon_simulation, calculate_utility
from api.engine.utils.simulation_metrics import compare_all_methods_mc
from api.engine.utils.simulation_multiwinner_utils import compare_multiwinner_methods
from api.engine.utils.real_election_data import analyze_real_election, list_elections
from api.engine.utils.blank_vote_rules import BlankVoteRule
from api.engine.constants import DEFAULT_ISSUES
from api.domain.simulations.helpers import (
    _parse_candidate_configs, _build_population,
    _build_scenario_candidates, _build_scenario_voters, _run_five_methods,
)
from api.engine.utils.logger import get_logger

log = get_logger(__name__)



# ── /simulations/bandwagon ──────────────────────────────────────────────────

def _bandwagon_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Cascading social influence across N rounds; measures how each method
    amplifies or resists bandwagon effects."""
    num_voters         = int(data.get("num_voters", 300))
    num_rounds         = int(data.get("num_rounds", 5))
    influence_strength = float(data.get("influence_strength", 0.3))
    ideology_dist      = data.get("ideology_distribution", "random")
    seed               = data.get("seed")
    raw_candidates     = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return {"error": "At least 2 candidates required"}, 400

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
        return result, 200
    except Exception as e:
        log.error("simulation.bandwagon.failed", exc_info=True)
        return {"error": str(e)}, 500




# ── /simulations/monte-carlo ────────────────────────────────────────────────

def _monte_carlo_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Run compare_all_methods_mc() N times in parallel and aggregate
    statistical distributions for each voting method.

    (Synchronous aggregation variant — distinct from the Socket.IO streaming
    Monte Carlo migrated in Phase 4.4.)
    """
    num_runs       = int(data.get("num_runs", 100))
    num_voters     = int(data.get("num_voters", 150))
    ideology_dist  = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    def _single_run(_: Any) -> Dict[str, Any]:
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

        winner_counts: Dict[str, Any]    = {m: defaultdict(int) for m in method_names}
        regrets:       Dict[str, List[float]] = {m: [] for m in method_names}
        satisfactions: Dict[str, List[float]] = {m: [] for m in method_names}
        condorcet_hits = {m: 0 for m in method_names}
        condorcet_runs = {m: 0 for m in method_names}
        agreement_counts: Dict[str, int] = defaultdict(int)
        agreement_total:  Dict[str, int] = defaultdict(int)
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

        def _ci95(values: List[float]) -> List[Optional[float]]:
            if len(values) < 2:
                return [None, None]
            mu = sum(values) / len(values)
            var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
            margin = 1.96 * math.sqrt(var) / math.sqrt(len(values))
            return [round(mu - margin, 6), round(mu + margin, 6)]

        def _entropy(dist: Dict[str, float], n_cand: int) -> float:
            e = -sum(p * math.log2(p) for p in dist.values() if p > 0)
            max_e = math.log2(n_cand) if n_cand > 1 else 1.0
            return round(e / max_e if max_e > 0 else 0.0, 4)

        methods_stats = {}
        for m in method_names:
            dist = {c: round(cnt / num_runs, 4) for c, cnt in winner_counts[m].items()}
            most_common: Optional[str] = max(winner_counts[m], key=lambda k: winner_counts[m][k]) if winner_counts[m] else None
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

        return {
            "num_runs":                     num_runs,
            "num_voters_per_run":           num_voters,
            "config": {
                "candidates":            [cfg["name"] for cfg in candidate_configs],
                "ideology_distribution": ideology_dist,
            },
            "methods":                      methods_stats,
            "condorcet_winner_exists_rate": round(condorcet_exists / num_runs, 4),
            "inter_method_agreement":       inter_agreement,
        }, 200

    except Exception as e:
        log.error("simulation.monte_carlo.failed", exc_info=True)
        return {"error": str(e)}, 500




# ── /simulations/multiwinner ────────────────────────────────────────────────

def _multiwinner_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Compare proportional multi-winner methods on a vote distribution."""
    party_votes = data.get("party_votes") or {}
    num_seats   = int(data.get("num_seats", 10))
    mode        = data.get("mode", "proportional")

    if not party_votes:
        return {"error": "party_votes is required"}, 400
    if num_seats < 1:
        return {"error": "num_seats must be >= 1"}, 400

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
        return result, 200
    except Exception as e:
        log.error("simulation.multiwinner.failed", exc_info=True)
        return {"error": str(e)}, 500




# ── /simulations/real-elections (GET) ───────────────────────────────────────

def _real_elections_list_worker(data: Dict[str, Any]) -> Tuple[Any, int]:
    """Return the list of available historical elections (no input). The body
    is a list (not a dict) — the only worker here that returns a non-dict."""
    return list_elections(), 200




# ── /simulations/blank-history (GET) ─────────────────────────────────────────

def _blank_history_worker(params: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Blank-vote time series for a country. 400 if missing, 404 if unknown."""
    from api.engine.utils.real_election_data import get_blank_history, list_blank_history_countries

    country_key = str(params.get("country", "")).strip()

    if not country_key:
        return {
            "error":     "Missing 'country' query parameter.",
            "available": list_blank_history_countries(),
        }, 400

    data = get_blank_history(country_key)
    if data is None:
        return {
            "error":     f"Unknown country '{country_key}'.",
            "available": list_blank_history_countries(),
        }, 404

    return data, 200




# ── /simulations/real-election (POST) ────────────────────────────────────────

def _real_election_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Analyse a real historical election under every voting method."""
    election_name = data.get("election_name", "")
    num_voters    = int(data.get("num_voters", 1000))
    blank_vote    = bool(data.get("blank_vote", False))
    try:
        blank_rule = BlankVoteRule(data.get("blank_rule", "symbolic"))
    except ValueError:
        blank_rule = BlankVoteRule.SYMBOLIC

    if not election_name:
        return {"error": "election_name is required"}, 400

    try:
        result = analyze_real_election(election_name, num_voters, blank_vote=blank_vote, blank_rule=blank_rule)
        return result, 200
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        log.error("simulation.real_election.failed", exc_info=True)
        return {"error": str(e)}, 500




# ── /simulations/constitutional-scenario ──────────────────────────────────

def _conclude_new_election(r1: Dict[str, Any], r2: Dict[str, Any], n_round2: int) -> str:
    blank_pct = round(r1.get("blank_pct", 0) * 100)
    r2_winners = [d["winner"] for d in r2["methods"].values() if d.get("winner") and d["winner"] != "Blank"]
    from collections import Counter
    winner2 = Counter(r2_winners).most_common(1)[0][0] if r2_winners else "personne"
    changed = sum(1 for m in r1["methods"] if r1["methods"][m].get("winner") != r2["methods"].get(m, {}).get("winner"))
    txt = (f"Dans ce scénario, le vote blanc ({blank_pct}% des voix) a provoqué une nouvelle élection. "
           f"Au second tour avec {n_round2} candidat(s), {winner2} a remporté l'élection pour la majorité des méthodes. ")
    txt += (f"{changed}/5 méthodes ont produit un résultat différent entre les deux tours — "
            "la pression du vote blanc a effectivement renouvelé l'offre politique." if changed > 0
            else "Malgré le renouvellement des candidats, les résultats n'ont pas changé — "
            "l'électorat reste fondamentalement insatisfait.")
    return txt


def _conclude_provisional(before: Dict[str, Any], after: Dict[str, Any], drift: float, duration: int) -> str:
    b_pct = round(before.get("blank_pct", 0) * 100)
    a_pct = round(after.get("blank_pct", 0) * 100)
    changed = sum(1 for m in before["methods"] if before["methods"][m].get("winner") != after["methods"].get(m, {}).get("winner"))
    txt = (f"Après {duration} mois de gouvernement provisoire, l'électorat a dérivé de ±{round(drift * 100, 1)}% "
           f"sur l'axe idéologique. Le vote blanc est passé de {b_pct}% à {a_pct}%. ")
    txt += (f"{changed}/5 méthodes ont changé de vainqueur : la dérive a modifié le rapport de force politique." if changed > 0
            else "Aucun changement de vainqueur : l'électorat reste structurellement défavorable aux candidats proposés, "
            "indépendamment du temps écoulé.")
    return txt


def _conclude_dissolution(multi: Dict[str, Any], plural_winner: str, num_seats: int) -> str:
    comp = multi.get("comparison", {})
    most_prop = comp.get("most_proportional", "sainte_lague")
    gallagher = multi.get(most_prop, {}).get("metrics", {}).get("gallagher_index")
    dhondt_seats = multi.get("dhondt", {}).get("seats", {}).get(plural_winner, 0)
    g_str = f"{gallagher:.3f}" if gallagher is not None else "?"
    return (f"Dans une assemblée de {num_seats} sièges, la méthode {most_prop.replace('_', ' ')} "
            f"produit la représentation la plus équitable (Gallagher = {g_str}). "
            f"En scrutin uninominal, {plural_winner} aurait dominé. "
            f"En D'Hondt, {plural_winner} obtient {dhondt_seats} siège(s) — "
            "illustrant comment la dissolution vers une assemblée proportionnelle redistribue le pouvoir.")


def _constitutional_scenario_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Simulate the constitutional aftermath of a blank-vote victory."""
    initial       = data.get("initial_election", {})
    scenario_type = data.get("scenario_type", "new_election")
    params        = data.get("params", {})

    issues = DEFAULT_ISSUES
    try:
        blank_rule = BlankVoteRule(initial.get("blank_rule", "competitive"))
    except ValueError:
        blank_rule = BlankVoteRule.COMPETITIVE

    cands_raw = initial.get("candidates", [])
    electorate = initial.get("electorate", {})

    real_candidates = _build_scenario_candidates(cands_raw, issues)
    if len(real_candidates) < 2:
        return {"error": "At least 2 real candidates required"}, 400

    # ── Scenario A — New election ──────────────────────────────────────────
    if scenario_type == "new_election":
        voters_r1 = _build_scenario_voters(electorate, issues)
        r1 = _run_five_methods(voters_r1, real_candidates, issues, blank_vote=True, blank_rule=blank_rule)

        new_cands_raw = params.get("new_candidates", cands_raw)
        new_candidates = _build_scenario_candidates(new_cands_raw, issues)
        if len(new_candidates) < 2:
            new_candidates = real_candidates  # fallback

        # Round 2 voters: same electorate but halved dissatisfaction (pressure released)
        base_dissat = float(electorate.get("dissatisfaction_rate", 0.2))
        voters_r2 = _build_scenario_voters(electorate, issues, dissatisfaction_override=base_dissat * 0.5)
        r2 = _run_five_methods(voters_r2, new_candidates, issues, blank_vote=True, blank_rule=blank_rule)

        return {
            "scenario_type": "new_election",
            "round1": r1,
            "round2": r2,
            "round2_candidate_names": [c["name"] for c in new_candidates],
            "conclusion": _conclude_new_election(r1, r2, len(new_candidates)),
        }, 200

    # ── Scenario B — Provisional government ───────────────────────────────
    elif scenario_type == "provisional":
        duration  = int(params.get("provisional_duration", 3))
        drift     = max(0.0, min(0.3, float(params.get("drift_magnitude", 0.05))))

        voters = _build_scenario_voters(electorate, issues)
        before = _run_five_methods(voters, real_candidates, issues, blank_vote=True, blank_rule=blank_rule)

        # Apply ideological drift to voters
        for v in voters:
            shift = _rng2.uniform(-drift, drift)
            v["political_lean_normalized"] = max(0.0, min(1.0, v["political_lean_normalized"] + shift))
            for iss in v.get("issue_positions", {}):
                v["issue_positions"][iss] = max(0.0, min(1.0, v["issue_positions"][iss] + shift * 0.5))

        after = _run_five_methods(voters, real_candidates, issues, blank_vote=True, blank_rule=blank_rule)

        return {
            "scenario_type": "provisional",
            "before_drift":  before,
            "after_drift":   after,
            "drift_applied": drift,
            "duration":      duration,
            "conclusion":    _conclude_provisional(before, after, drift, duration),
        }, 200

    # ── Scenario C — Dissolution ───────────────────────────────────────────
    elif scenario_type == "dissolution":
        num_seats = max(10, int(params.get("num_seats", 100)))

        voters = _build_scenario_voters(electorate, issues)
        initial_result = _run_five_methods(voters, real_candidates, issues, blank_vote=False)

        # Derive party votes from first-choice utilities
        from collections import Counter
        utils_map = {
            v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"] for c in real_candidates}
            for v in voters
        }
        rankings = [sorted([c["name"] for c in real_candidates], key=lambda n: -utils_map[v["id"]][n]) for v in voters]
        first_choices = Counter(r[0] for r in rankings if r)
        party_votes: Dict[str, float] = {str(name): float(count) for name, count in first_choices.items()}

        multi = compare_multiwinner_methods(party_votes=party_votes, num_seats=num_seats)
        multi["party_votes"] = party_votes
        multi["num_seats"]   = num_seats

        plural_winner = initial_result["methods"].get("plurality", {}).get("winner")

        return {
            "scenario_type":   "dissolution",
            "initial_methods": initial_result,
            "multiwinner":     multi,
            "uninominal_winner": plural_winner,
            "party_votes":     party_votes,
            "num_seats":       num_seats,
            "conclusion":      _conclude_dissolution(multi, plural_winner or "?", num_seats),
        }, 200

    else:
        return {"error": f"Unknown scenario_type '{scenario_type}'"}, 400




# ── /simulations/blank-contagion ─────────────────────────────────────────────

def _blank_contagion_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Run a SIS blank-vote contagion simulation."""
    from api.engine.utils.blank_contagion import simulate_blank_contagion

    try:
        num_voters         = max(10,  min(1_000, int(data.get("num_voters",         300))))
        initial_blank_rate = max(0.0, min(1.0,   float(data.get("initial_blank_rate", 0.10))))
        contagion_rate     = max(0.0, min(1.0,   float(data.get("contagion_rate",    0.30))))
        recovery_rate      = max(0.0, min(1.0,   float(data.get("recovery_rate",     0.15))))
        num_rounds         = max(1,   min(50,    int(data.get("num_rounds",          15))))
        network_type       = str(data.get("network_type", "random"))
        seed_raw           = data.get("seed")
        seed               = int(seed_raw) if seed_raw is not None else None
    except (TypeError, ValueError) as exc:
        return {"error": f"Invalid parameter: {exc}"}, 400

    try:
        result = simulate_blank_contagion(
            num_voters=num_voters,
            initial_blank_rate=initial_blank_rate,
            contagion_rate=contagion_rate,
            recovery_rate=recovery_rate,
            num_rounds=num_rounds,
            network_type=network_type,
            seed=seed,
        )
        return result, 200
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except Exception as exc:
        log.error("simulation.blank_contagion.failed", exc_info=True)
        return {"error": str(exc)}, 500


