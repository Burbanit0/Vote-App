"""
api.domain.election.workers_mechanisms — electoral-mechanism workers, split out
of the workers.py monolith (incremental decomposition).

Pure `data: dict -> (body, http_status)` workers: adaptive (tactical) voting,
historical replay, Condorcet-jury theorem, differential abstention, STV,
gerrymandering, multi-winner comparison. Depends only on the engine utils +
the shared ._electorate / ._helpers.
"""
from __future__ import annotations

import math  # noqa: F401
import random as _random
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

import numpy as _np

from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.simulation_ranked_utils import (
    get_plurality_winner, get_condorcet_winner, get_irv_winner,
    get_borda_winner, get_schulze_winner, get_approval_winner_sincere,
)
from api.engine.utils.simulation_multiwinner_utils import (
    get_stv_result, get_dhondt_winners, get_spav_result, get_phragmen_result,
    get_equal_shares_result, check_justified_representation,
)
from ._electorate import _build_base_electorate
from ._helpers import dhondt as _dhondt


# ── Adaptive voting endpoint ──────────────────────────────────────────────────

_METHOD_WINNERS: Dict[str, Any] = {
    "plurality": get_plurality_winner,
    "irv":       get_irv_winner,
    "borda":     get_borda_winner,
    "schulze":   get_schulze_winner,
}


def _compute_winner(
    rankings: list[list[str]],
    utilities: Dict[Any, Dict[str, float]],
    method: str,
) -> Optional[str]:
    """Dispatch to the correct winner function for the given method."""
    if method == "approval":
        return get_approval_winner_sincere(utilities)
    fn = _METHOD_WINNERS.get(method, get_plurality_winner)
    result: Optional[str] = fn(rankings)
    return result


def _tactical_vote(
    voter_id: Any,
    sincere_ranking: list[str],
    utilities: Dict[str, float],
    polls: Dict[str, float],
    strategic_threshold: float,
) -> list[str]:
    """
    Compute a tactical ranking for one strategic voter.

    A voter becomes tactical when their 1st choice polls below
    `strategic_threshold` (as a fraction).  They then move the
    viable candidate with the highest personal utility to the top.
    Viable = polls ≥ strategic_threshold.  Ties broken by utility.
    """
    first_choice = sincere_ranking[0] if sincere_ranking else ""
    if polls.get(first_choice, 0) >= strategic_threshold:
        return sincere_ranking  # already competitive — stay sincere

    viable = [n for n in sincere_ranking if polls.get(n, 0) >= strategic_threshold]
    if not viable:
        return sincere_ranking  # no viable alternative — stay sincere

    # Best viable = highest utility among viable candidates
    best = max(viable, key=lambda n: utilities.get(n, 0.0))
    if best == first_choice:
        return sincere_ranking

    new_ranking = [best] + [n for n in sincere_ranking if n != best]
    return new_ranking


def _adaptive_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /adaptive — N rounds of adaptive/tactical voting."""
    num_voters          = max(50, min(1000, int(data.get("num_voters",          300))))
    ideology            = str(data.get("ideology",            "random"))
    seed                = int(data.get("seed",                 42))
    num_rounds          = max(1,  min(10,  int(data.get("num_rounds",           5))))
    method              = str(data.get("method",              "plurality"))
    strategic_threshold = max(0.0, min(1.0, float(data.get("strategic_threshold", 0.15))))
    cand_specs          = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Each voter's sincere ranking (fixed for the whole simulation)
    sincere_rankings: Dict[Any, list[str]] = {}
    for v in voters:
        uid = v["id"]
        sincere_rankings[uid] = sorted(
            true_utilities[uid].keys(), key=lambda n: -true_utilities[uid][n]
        )

    # ── Round 0: sincere vote ─────────────────────────────────────────────
    rounds_out: list[Dict[str, Any]] = []
    polls: Dict[str, float] = {n: 1.0 / len(cand_names) for n in cand_names}
    previous_winner: Optional[str] = None
    converged       = False
    convergence_round: Optional[int] = None
    stable_count    = 0

    # Compute global sincere winner (used for drift comparison at the end)
    sincere_all_rankings = [sincere_rankings[v["id"]] for v in voters]
    sincere_final_winner = _compute_winner(sincere_all_rankings, true_utilities, method)

    # Voter snapshot for ideology overlay (max 200 points)
    snap_indices = list(range(min(200, len(voters))))

    for rnd in range(num_rounds):
        # Determine effective ranking for each voter this round
        effective_rankings: list[list[str]] = []
        n_strategic = 0

        for v in voters:
            uid       = v["id"]
            propensity: float = float(v.get("strategic_propensity", 0.2))
            roll: float = float(_random.random())
            if rnd > 0 and propensity > roll:
                tactical = _tactical_vote(
                    uid, sincere_rankings[uid], true_utilities[uid], polls, strategic_threshold
                )
                effective_rankings.append(tactical)
                if tactical[0] != sincere_rankings[uid][0]:
                    n_strategic += 1
            else:
                effective_rankings.append(sincere_rankings[uid])

        # Run the chosen method
        eff_utils: Dict[Any, Dict[str, float]] = {
            v["id"]: true_utilities[v["id"]] for v in voters
        }
        winner = _compute_winner(effective_rankings, eff_utils, method)

        # Vote shares from first-choice counts
        first_choice_counts: Counter[str] = Counter(
            r[0] for r in effective_rankings if r
        )
        total = len(voters) or 1
        vote_shares = {n: round(first_choice_counts.get(n, 0) / total, 4) for n in cand_names}

        # Sincere vote shares (always from round-0 sincere vote for reference)
        sincere_fc: Counter[str] = Counter(
            sincere_rankings[v["id"]][0] for v in voters
            if sincere_rankings[v["id"]]
        )
        sincere_shares = {n: round(sincere_fc.get(n, 0) / total, 4) for n in cand_names}

        # Voter snapshot (strategic change indicator)
        voter_snaps = []
        for i in snap_indices:
            v   = voters[i]
            uid = v["id"]
            eff = effective_rankings[i] if i < len(effective_rankings) else sincere_rankings[uid]
            sx  = round(2.0 * v["issue_positions"].get("economy",       0.5) - 1.0, 3)
            sy  = round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3)
            voter_snaps.append({
                "id":            uid,
                "x":             sx,
                "y":             sy,
                "sincere_vote":  sincere_rankings[uid][0] if sincere_rankings[uid] else "",
                "effective_vote": eff[0] if eff else "",
                "tactical":      eff[0] != sincere_rankings[uid][0] if eff else False,
            })

        rounds_out.append({
            "round":               rnd,
            "vote_shares":         vote_shares,
            "sincere_shares":      sincere_shares,
            "winner":              winner,
            "sincere_winner":      sincere_final_winner,
            "strategic_voters_pct": round(n_strategic / total, 4),
            "voter_snapshot":      voter_snaps,
        })

        # Update polls for next round
        polls = vote_shares

        # Convergence check: winner stable for 2 consecutive rounds
        if winner == previous_winner:
            stable_count += 1
            if stable_count >= 2 and not converged:
                converged = True
                convergence_round = rnd - 1
        else:
            stable_count = 0
        previous_winner = winner

    # ── Strategic drift ────────────────────────────────────────────────────
    # Ideological distance between sincere winner and final winner
    def _ideology_pos(name: str) -> float:
        c = next((c for c in candidates if c["name"] == name), None)
        return round(2.0 * c["ideology_position"] - 1.0, 3) if c else 0.0

    final_winner = rounds_out[-1]["winner"] if rounds_out else sincere_final_winner
    if sincere_final_winner and final_winner:
        strategic_drift = round(
            abs(_ideology_pos(final_winner) - _ideology_pos(sincere_final_winner)), 4
        )
    else:
        strategic_drift = 0.0

    return {
        "rounds":             rounds_out,
        "converged":          converged,
        "convergence_round":  convergence_round,
        "final_winner":       final_winner,
        "sincere_winner":     sincere_final_winner,
        "strategic_drift":    strategic_drift,
        "candidates":         [
            {"name": c["name"], "x": _ideology_pos(c["name"])}
            for c in candidates
        ],
    }, 200


# ── Historical replay ─────────────────────────────────────────────────────────

_REPLAY_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "france2002": {
        "name":       "France 2002 — 1er tour",
        "ideology":   "left_skewed",
        "num_voters": 400,
        "real_winner": "Chirac",
        "candidates": [
            {"name": "Chirac",  "x":  0.30, "y":  0.10},
            {"name": "Jospin",  "x": -0.30, "y": -0.10},
            {"name": "Le Pen",  "x":  0.85, "y":  0.20},
            {"name": "Bayrou",  "x":  0.05, "y":  0.00},
        ],
    },
    "usa1992": {
        "name":       "USA 1992",
        "ideology":   "centrist",
        "num_voters": 400,
        "real_winner": "Clinton",
        "candidates": [
            {"name": "Clinton", "x": -0.20, "y":  0.00},
            {"name": "Bush",    "x":  0.30, "y":  0.10},
            {"name": "Perot",   "x":  0.00, "y": -0.10},
        ],
    },
    "germany2021": {
        "name":       "Allemagne 2021",
        "ideology":   "centrist",
        "num_voters": 400,
        "real_winner": "Scholz (SPD)",
        "candidates": [
            {"name": "Scholz (SPD)",     "x": -0.20, "y": -0.10},
            {"name": "Laschet (CDU)",    "x":  0.20, "y":  0.00},
            {"name": "Baerbock (Verts)", "x": -0.45, "y":  0.35},
            {"name": "Lindner (FDP)",    "x":  0.40, "y": -0.15},
            {"name": "Weidel (AfD)",     "x":  0.75, "y":  0.10},
        ],
    },
    "condorcet_cycle": {
        "name":       "Cycle de Condorcet",
        "ideology":   "polarized",
        "num_voters": 300,
        "real_winner": "—",
        "candidates": [
            {"name": "Alice", "x":  0.00, "y":  0.55},
            {"name": "Bob",   "x": -0.55, "y": -0.30},
            {"name": "Carol", "x":  0.55, "y": -0.30},
        ],
    },
}


def _historical_replay_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /historical-replay — extracted for FastAPI v2."""
    scenario_id = str(data.get("scenario_id", "france2002"))
    overrides   = data.get("overrides") or []
    num_days    = max(1, min(60, int(data.get("num_days", 30))))
    seed        = int(data.get("seed", 42))

    cfg = _REPLAY_SCENARIOS.get(scenario_id)
    if not cfg:
        return {"error": f"Unknown scenario: {scenario_id}"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    # Apply user overrides to candidate positions
    override_map: Dict[str, Dict[str, float]] = {
        o["name"]: {"x": float(o["x"]), "y": float(o["y"])}
        for o in overrides if "name" in o
    }
    cand_specs: list[Dict[str, Any]] = [
        {**c, **override_map[c["name"]]} if c["name"] in override_map else c
        for c in cfg["candidates"]
    ]

    candidates, voters, base_utilities, cand_names = _build_base_electorate(
        cand_specs, int(cfg["num_voters"]), str(cfg["ideology"]), seed, issues
    )

    # ── Day-by-day Brownian campaign simulation ────────────────────────────
    sigma = 0.018
    current_u: Dict[Any, Dict[str, float]] = {
        v["id"]: dict(base_utilities[v["id"]]) for v in voters
    }
    n_cands   = len(cand_names)
    days_out: list[Dict[str, Any]] = []

    for day in range(num_days + 1):
        if day > 0:
            shocks = {n: float(_np.random.normal(0, sigma)) for n in cand_names}
            for v in voters:
                uid = v["id"]
                for n in cand_names:
                    current_u[uid][n] = float(
                        max(0.01, min(0.99, current_u[uid][n] + shocks[n]))
                    )

        # First-choice vote shares
        fc: Counter[str] = Counter()
        for v in voters:
            uid  = v["id"]
            best = max(current_u[uid], key=lambda k: current_u[uid][k])
            fc[best] += 1
        total      = len(voters) or 1
        vote_shares = {n: round(fc.get(n, 0) / total, 4) for n in cand_names}

        # Rankings for Condorcet / Borda
        rankings: list[list[str]] = []
        for v in voters:
            uid = v["id"]
            rankings.append(
                sorted(current_u[uid].keys(), key=lambda k: -current_u[uid][k])
            )

        condorcet_w  = get_condorcet_winner(rankings)
        winner_fptp  = max(vote_shares, key=lambda k: vote_shares[k])
        borda_scores: Dict[str, float] = {n: 0.0 for n in cand_names}
        for r in rankings:
            for i, name in enumerate(r):
                borda_scores[name] += n_cands - 1 - i
        winner_borda = max(borda_scores, key=lambda k: borda_scores[k])

        days_out.append({
            "day":              day,
            "vote_shares":      vote_shares,
            "winner_fptp":      winner_fptp,
            "winner_condorcet": condorcet_w,
            "winner_borda":     winner_borda,
        })

    final_day   = days_out[-1]
    real_winner = str(cfg["real_winner"])
    differs     = final_day["winner_fptp"] != real_winner

    if differs and override_map:
        moved   = ", ".join(override_map.keys())
        note_fr = (f"En déplaçant {moved}, le vainqueur FPTP devient "
                   f"{final_day['winner_fptp']} au lieu de {real_winner}. "
                   "Le repositionnement idéologique a suffi à réécrire l'histoire.")
        note_en = (f"By moving {moved}, the FPTP winner becomes "
                   f"{final_day['winner_fptp']} instead of {real_winner}. "
                   "The ideological shift was enough to rewrite history.")
    elif differs:
        note_fr = (f"La simulation donne {final_day['winner_fptp']} "
                   f"(contre {real_winner} historiquement).")
        note_en = (f"The simulation gives {final_day['winner_fptp']} "
                   f"(vs {real_winner} historically).")
    else:
        note_fr = (f"La simulation converge vers {real_winner}, comme dans l'histoire réelle. "
                   "Déplacez un candidat pour explorer des scénarios alternatifs.")
        note_en = (f"The simulation converges on {real_winner}, matching historical reality. "
                   "Move a candidate to explore alternative scenarios.")

    return {
        "scenario": {"id": scenario_id, "name": cfg["name"], "real_winner": real_winner},
        "candidates": [
            {"name": c["name"], "x": float(c["x"]), "y": float(c["y"]),
             "modified": c["name"] in override_map}
            for c in cand_specs
        ],
        "days":  days_out,
        "final": {
            "winner_fptp":         final_day["winner_fptp"],
            "winner_condorcet":    final_day["winner_condorcet"],
            "winner_borda":        final_day["winner_borda"],
            "differs_from_real":   differs,
            "pedagogical_note":    note_fr,
            "pedagogical_note_en": note_en,
        },
    }, 200


# ── Jury theorem endpoint ─────────────────────────────────────────────────────

def _jury_theoretical(n: int, p: float) -> float:
    """
    Condorcet jury theorem: probability that majority is correct.
    P = Σ C(n,k) p^k (1-p)^(n-k)  for k = ceil((n+1)/2) … n
    """
    threshold = n // 2 + 1
    acc = 0.0
    q   = 1.0 - p
    for k in range(threshold, n + 1):
        acc += math.comb(n, k) * (p ** k) * (q ** (n - k))
    return min(1.0, acc)


def _generate_jury_ballots(
    num_voters: int,
    options: List[str],
    correct_idx: int,
    competence: float,
    rng: _random.Random,
) -> List[List[str]]:
    """
    Each voter independently ranks options.
    With probability `competence` they rank the correct option first;
    with probability 1-competence they rank a random wrong option first.
    The remainder of the ranking is shuffled uniformly.
    """
    correct = options[correct_idx]
    wrong   = [o for o in options if o != correct]
    ballots: List[List[str]] = []

    for _ in range(num_voters):
        rest = list(options)
        if rng.random() < competence:
            first = correct
        else:
            first = rng.choice(wrong)
        rest.remove(first)
        rng.shuffle(rest)
        ballots.append([first] + rest)

    return ballots


def _jury_approval_winner(
    ballots: List[List[str]],
    num_options: int,
) -> Optional[str]:
    """Approval: each voter approves top ceil(num_options/2) of their ranking."""
    top_k = max(1, (num_options + 1) // 2)
    counts: Counter[str] = Counter()
    for b in ballots:
        for opt in b[:top_k]:
            counts[opt] += 1
    return counts.most_common(1)[0][0] if counts else None


_JURY_METHODS = ["plurality", "borda", "irv", "approval", "schulze"]


def _run_jury_simulation(
    num_voters:   int,
    options:      List[str],
    correct_idx:  int,
    competence:   float,
    num_sims:     int,
    rng:          _random.Random,
) -> Dict[str, float]:
    """
    Run num_sims Monte Carlo trials.
    Returns {method: accuracy_fraction}.
    """
    correct   = options[correct_idx]
    successes: Dict[str, int] = {m: 0 for m in _JURY_METHODS}

    for _ in range(num_sims):
        ballots = _generate_jury_ballots(num_voters, options, correct_idx, competence, rng)

        winners = {
            "plurality": get_plurality_winner(ballots),
            "borda":     get_borda_winner(ballots),
            "irv":       get_irv_winner(ballots),
            "approval":  _jury_approval_winner(ballots, len(options)),
            "schulze":   get_schulze_winner(ballots),
        }

        for m, w in winners.items():
            if w == correct:
                successes[m] += 1

    return {m: round(successes[m] / num_sims, 4) for m in _JURY_METHODS}


def _jury_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /jury — extracted for FastAPI v2 reuse."""
    num_voters        = max(10, min(500, int(data.get("num_voters",        100))))
    num_options       = max(2,  min(5,   int(data.get("num_options",         2))))
    correct_idx       = max(0,  min(num_options - 1,
                                    int(data.get("correct_option_index",    0))))
    voter_competence  = max(0.50, min(1.0, float(data.get("voter_competence",  0.70))))
    num_simulations   = max(50,  min(500,  int(data.get("num_simulations",   200))))
    seed              = int(data.get("seed", 42))

    options = [f"Option {i}" for i in range(num_options)]
    rng     = _random.Random(seed)

    # ── Main simulation ───────────────────────────────────────────────────
    accuracies = _run_jury_simulation(
        num_voters, options, correct_idx, voter_competence, num_simulations, rng
    )

    theoretical = _jury_theoretical(num_voters, voter_competence)
    majority_acc = accuracies.get("plurality", 0.0)

    methods_out: Dict[str, Any] = {}
    for m, acc in accuracies.items():
        methods_out[m] = {
            "accuracy":       acc,
            "beats_majority": acc > majority_acc or m == "plurality",
            "beats_theory":   acc > theoretical,
        }

    best_method  = max(accuracies, key=lambda k: accuracies[k])
    worst_method = min(accuracies, key=lambda k: accuracies[k])

    # ── Competence curve (20 points, 100 sims each for speed) ────────────
    curve_rng = _random.Random(seed + 1)
    curve_sims = max(50, min(150, num_simulations // 2))
    curve_points: List[Dict[str, Any]] = []
    for step in range(20):
        p = 0.51 + step * (0.48 / 19)   # 0.51 → 0.99
        pt_acc = _run_jury_simulation(
            num_voters, options, correct_idx, round(p, 3), curve_sims, curve_rng
        )
        point: Dict[str, Any] = {
            "competence": round(p, 3),
            "theoretical": round(_jury_theoretical(num_voters, p), 4),
        }
        point.update({m: pt_acc[m] for m in _JURY_METHODS})
        curve_points.append(point)

    # ── Pedagogical note ──────────────────────────────────────────────────
    pct_theory = round(theoretical * 100, 1)
    pct_best   = round(accuracies[best_method] * 100, 1)
    delta      = round((accuracies[best_method] - theoretical) * 100, 1)
    if delta > 0:
        note_fr = (
            f"Avec P={voter_competence} et {num_voters} électeurs, "
            f"la théorie prédit {pct_theory}%. "
            f"{best_method.capitalize()} atteint {pct_best}% "
            f"(+{delta}% vs théorie) — il agrège mieux l'information collective "
            f"que la simple majorité."
        )
        note_en = (
            f"With P={voter_competence} and {num_voters} voters, "
            f"theory predicts {pct_theory}%. "
            f"{best_method.capitalize()} reaches {pct_best}% "
            f"(+{delta}% vs theory) — it aggregates collective information "
            f"better than simple majority."
        )
    else:
        note_fr = (
            f"Avec P={voter_competence} et {num_voters} électeurs, "
            f"la théorie prédit {pct_theory}%. "
            f"Aucune méthode ne dépasse la prédiction théorique — "
            f"la majorité reste la meilleure agrégation dans ce scénario."
        )
        note_en = (
            f"With P={voter_competence} and {num_voters} voters, "
            f"theory predicts {pct_theory}%. "
            f"No method exceeds the theoretical prediction — "
            f"majority rule is the best aggregation in this scenario."
        )

    return {
        "theoretical_accuracy": round(theoretical, 4),
        "methods":              methods_out,
        "best_method":          best_method,
        "worst_method":         worst_method,
        "voter_competence":     voter_competence,
        "num_voters":           num_voters,
        "competence_curve":     curve_points,
        "pedagogical_note":     note_fr,
        "pedagogical_note_en":  note_en,
    }, 200


# ── Differential abstention endpoint ─────────────────────────────────────────

def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    return 1.0 / (1.0 + float(_np.exp(-min(max(x, -30.0), 30.0))))


def _abstention_prob(
    poll_gap:             float,
    utility_gap:          float,
    demobilization_factor: float,
    poll_influence:        float,
) -> float:
    """
    P(abstention) for one voter in one round.

    Scales to 0 when demobilization_factor=0 (guaranteed no abstention).
    Uses a sigmoid of the combined demobilization signal, multiplied by
    demobilization_factor and poll_influence as outer scale factors.

    poll_gap    = fraction of voters NOT preferring the same candidate as v
                  (high → v's candidate is trailing in the polls)
    utility_gap = 1 - max_utility of v (high → v is indifferent to outcome)
    """
    if demobilization_factor <= 0.0:
        return 0.0
    # Inner signal: shifts sigmoid so neutral inputs give ~0.2 probability
    signal = poll_gap * 3.0 + utility_gap * 1.5 - 1.0
    p = demobilization_factor * _sigmoid(signal) * poll_influence
    return max(0.0, min(1.0, p))


def _abstention_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /abstention — extracted for FastAPI v2 reuse."""

    num_voters             = max(50,  min(1000, int(data.get("num_voters", 300))))
    ideology               = str(data.get("ideology", "random"))
    seed                   = int(data.get("seed", 42))
    demobilization_factor  = max(0.0, min(1.0, float(data.get("demobilization_factor", 0.5))))
    poll_influence         = max(0.0, min(1.0, float(data.get("poll_influence", 0.8))))
    num_rounds             = max(1, min(5, int(data.get("num_rounds", 3))))
    cand_specs             = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Voter positions for the abstention_map (SVG ideology overlay)
    voter_positions: list[Dict[str, Any]] = [
        {
            "id": v["id"],
            "x":  round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3),
            "y":  round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
        }
        for v in voters
    ]

    # Each voter's preferred candidate (highest true utility)
    voter_preferred: Dict[Any, str] = {
        v["id"]: max(true_utilities[v["id"]], key=lambda k: true_utilities[v["id"]][k])
        for v in voters
    }

    # Round 0: sincere vote (no polls → no abstention)
    sincere_fc: Counter[str] = Counter(voter_preferred.values())
    total_sincere = len(voters) or 1
    polls: Dict[str, float] = {n: sincere_fc.get(n, 0) / total_sincere for n in cand_names}

    def _run_round_fptp(active_voters: list[Dict[str, Any]]) -> str:
        fc: Counter[str] = Counter(voter_preferred[v["id"]] for v in active_voters)
        return max(fc, key=lambda k: fc[k]) if fc else cand_names[0]

    def _run_round_condorcet(active_voters: list[Dict[str, Any]]) -> Optional[str]:
        rankings = [
            sorted(true_utilities[v["id"]].keys(), key=lambda k: -true_utilities[v["id"]][k])
            for v in active_voters
        ]
        return get_condorcet_winner(rankings)

    sincere_winner = _run_round_fptp(voters)

    rounds_out: list[Dict[str, Any]] = []

    for rnd in range(num_rounds + 1):
        if rnd == 0:
            # Sincere round — everyone votes
            active   = voters
            abs_probs = {v["id"]: 0.0 for v in voters}
            abstained = set[Any]()
        else:
            # Determine P(abstention) for each voter from last-round polls
            abs_probs = {}
            abstained = set()
            for v in voters:
                uid      = v["id"]
                pref     = voter_preferred[uid]
                poll_gap = max(0.0, 1.0 - polls.get(pref, 0.0))
                max_util = max(true_utilities[uid].values(), default=0.5)
                util_gap = max(0.0, 1.0 - max_util)
                p        = _abstention_prob(poll_gap, util_gap,
                                             demobilization_factor, poll_influence)
                abs_probs[uid] = round(p, 4)
                if _random.random() < p:
                    abstained.add(uid)
            active = [v for v in voters if v["id"] not in abstained]

        # Vote shares among active voters
        fc: Counter[str] = Counter()
        for v in active:
            fc[voter_preferred[v["id"]]] += 1
        total_active = len(active) or 1
        vote_shares = {n: round(fc.get(n, 0) / total_active, 4) for n in cand_names}

        winner_fptp      = _run_round_fptp(active)
        winner_condorcet = _run_round_condorcet(active)

        # Build abstention_map (max 300 voters for performance)
        snap_indices = list(range(min(300, len(voters))))
        abs_map = [
            {
                **voter_positions[i],
                "preferred":        voter_preferred[voters[i]["id"]],
                "abstained":        voters[i]["id"] in abstained,
                "prob_abstention":  abs_probs.get(voters[i]["id"], 0.0),
            }
            for i in snap_indices
        ]

        rounds_out.append({
            "round":          rnd,
            "turnout":        round(len(active) / (len(voters) or 1), 4),
            "vote_shares":    vote_shares,
            "winner_fptp":    winner_fptp,
            "winner_condorcet": winner_condorcet,
            "abstention_map": abs_map,
        })

        # Update polls for next round
        polls = vote_shares

    final_winner   = rounds_out[-1]["winner_fptp"]
    winner_changed = final_winner != sincere_winner

    # Turnout by camp (average participation rate per preferred candidate)
    camp_votes:  Dict[str, int] = {n: 0 for n in cand_names}
    camp_total:  Dict[str, int] = {n: 0 for n in cand_names}
    last_abs_map = rounds_out[-1]["abstention_map"]
    for p in last_abs_map:
        pref = p["preferred"]
        camp_total[pref] = camp_total.get(pref, 0) + 1
        if not p["abstained"]:
            camp_votes[pref] = camp_votes.get(pref, 0) + 1
    turnout_by_camp = {
        n: round(camp_votes.get(n, 0) / max(camp_total.get(n, 1), 1), 4)
        for n in cand_names
    }

    # ── Per-method winners (with and without abstention) ──────────────────
    # Enables the LabCentralView pinned matrix to show how abstention
    # affects every voting method, not just plurality.
    try:
        sincere_compare = compare_all_methods(voters, candidates, issues)
        final_compare   = compare_all_methods(active, candidates, issues)
        sincere_winners_by_method = {
            m: data.get("winner")
            for m, data in sincere_compare.get("methods", {}).items()
        }
        winners_by_method = {
            m: data.get("winner")
            for m, data in final_compare.get("methods", {}).items()
        }
    except Exception:  # pylint: disable=broad-except
        sincere_winners_by_method = {}
        winners_by_method = {}

    return {
        "rounds":          rounds_out,
        "sincere_winner":  sincere_winner,
        "final_winner":    final_winner,
        "winner_changed":  winner_changed,
        "turnout_by_camp": turnout_by_camp,
        "candidates":      [{"name": c["name"]} for c in candidates],
        "sincere_winners_by_method": sincere_winners_by_method,
        "winners_by_method":         winners_by_method,
    }, 200


# ── STV endpoint ──────────────────────────────────────────────────────────────

def _stv_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /stv — extracted for FastAPI v2."""
    num_voters = max(50,  min(1000, int(data.get("num_voters",  300))))
    ideology   = str(data.get("ideology",  "random"))
    seed       = int(data.get("seed",        42))
    num_seats  = max(2,  min(10,  int(data.get("num_seats",     5))))
    quota_type = str(data.get("quota_type", "droop"))
    cand_specs = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
        {"name": "Dave",  "x": -0.2, "y":  0.5},
    ])[:8]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400
    if num_seats >= len(cand_specs):
        return {"error": "num_seats must be less than number of candidates"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Build full ranked ballots (sincere, by utility)
    rankings: list[list[str]] = []
    for v in voters:
        uid = v["id"]
        rankings.append(
            sorted(true_utilities[uid].keys(), key=lambda k: -true_utilities[uid][k])
        )

    # ── STV ────────────────────────────────────────────────────────────────
    stv_raw = get_stv_result(rankings, num_seats, quota_type)

    # ── D'Hondt (from first-choice vote shares) ───────────────────────────
    first_choice: Counter[str] = Counter(r[0] for r in rankings if r)
    total = len(rankings) or 1
    vote_shares = {n: first_choice.get(n, 0) / total for n in cand_names}
    dhondt_seats = get_dhondt_winners(vote_shares, num_seats)

    # ── FPTP multi-seat (top-N by first-choice votes) ─────────────────────
    top_n    = sorted(cand_names, key=lambda c: -first_choice.get(c, 0))[:num_seats]
    fptp_seats: Dict[str, int] = {c: (1 if c in top_n else 0) for c in cand_names}

    # ── Distortion metrics ────────────────────────────────────────────────
    stv_seat_dict: Dict[str, int] = {c: (1 if c in stv_raw["elected"] else 0) for c in cand_names}

    def _seat_distortion(a: Dict[str, int], b: Dict[str, int]) -> float:
        return sum(abs(a.get(c, 0) - b.get(c, 0)) for c in cand_names) / 2

    return {
        "stv": {
            "elected":  stv_raw["elected"],
            "quota":    stv_raw["quota"],
            "rounds":   stv_raw["rounds"],
            "seats":    stv_seat_dict,
        },
        "dhondt": {
            "seats":    dhondt_seats,
            "elected":  [c for c, s in sorted(dhondt_seats.items(), key=lambda kv: -kv[1]) if s > 0],
        },
        "fptp": {
            "seats":    fptp_seats,
            "elected":  top_n,
        },
        "vote_shares":           {n: round(vote_shares[n], 4) for n in cand_names},
        "num_seats":             num_seats,
        "quota":                 stv_raw["quota"],
        "quota_type":            quota_type,
        "distortion_stv_dhondt": round(_seat_distortion(stv_seat_dict, dhondt_seats), 3),
        "distortion_stv_fptp":   round(_seat_distortion(stv_seat_dict, fptp_seats), 3),
        "candidates":            cand_names,
    }, 200


# ── Gerrymandering endpoint ───────────────────────────────────────────────────

def _closest_district(
    vx: float, vy: float,
    districts: List[Dict[str, Any]],
) -> int:
    """Return the id of the district whose centroid is closest to (vx, vy)."""
    best_id: int = int(districts[0]["id"])
    best_dist = float("inf")
    for d in districts:
        b   = d["bounds"]
        cx  = (b["x_min"] + b["x_max"]) / 2
        cy  = (b["y_min"] + b["y_max"]) / 2
        dist = (vx - cx) ** 2 + (vy - cy) ** 2
        if dist < best_dist:
            best_dist = dist
            best_id   = int(d["id"])
    return best_id


def _gerrymander_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /gerrymander — extracted for FastAPI v2."""
    num_voters = max(50,  min(1000, int(data.get("num_voters",  300))))
    ideology   = str(data.get("ideology",  "random"))
    seed       = int(data.get("seed",        42))
    cand_specs = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
    ])[:6]
    districts_raw: List[Dict[str, Any]] = data.get("districts") or []

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400
    if not districts_raw:
        return {"error": "At least 1 district required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Map each voter's 2-D position
    voter_positions: Dict[Any, tuple[float, float]] = {
        v["id"]: (
            round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3),
            round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
        )
        for v in voters
    }

    # Each voter's preferred candidate (highest true utility)
    voter_preferred: Dict[Any, str] = {
        v["id"]: max(true_utilities[v["id"]], key=lambda k: true_utilities[v["id"]][k])
        for v in voters
    }

    # ── Assign voters to districts ────────────────────────────────────────
    # district_id → list of voter ids
    district_members: Dict[int, List[Any]] = {d["id"]: [] for d in districts_raw}
    unassigned: List[Any] = []

    for v in voters:
        uid = v["id"]
        vx, vy = voter_positions[uid]
        matched = [
            d for d in districts_raw
            if d["bounds"]["x_min"] <= vx <= d["bounds"]["x_max"]
            and d["bounds"]["y_min"] <= vy <= d["bounds"]["y_max"]
        ]
        if len(matched) == 1:
            district_members[matched[0]["id"]].append(uid)
        elif len(matched) > 1:
            # Multiple districts overlap — pick the smallest area
            def _area(d: Dict[str, Any]) -> float:
                b = d["bounds"]
                return float(b["x_max"] - b["x_min"]) * float(b["y_max"] - b["y_min"])
            best = min(matched, key=_area)
            district_members[best["id"]].append(uid)
        else:
            unassigned.append(uid)

    # Assign unmatched voters to nearest district
    for uid in unassigned:
        vx, vy = voter_positions[uid]
        nearest = _closest_district(vx, vy, districts_raw)
        district_members[nearest].append(uid)

    # ── Per-district FPTP ─────────────────────────────────────────────────
    district_results: List[Dict[str, Any]] = []
    parliament_gerry: Dict[str, int] = {n: 0 for n in cand_names}

    national_fc:    Counter[str] = Counter()
    national_total: int          = 0

    for d in districts_raw:
        members = district_members[d["id"]]
        if not members:
            district_results.append({
                "id": d["id"], "num_voters": 0,
                "winner": None, "vote_shares": {},
            })
            continue

        fc: Counter[str] = Counter(voter_preferred[uid] for uid in members)
        total = len(members)
        vote_shares = {n: round(fc.get(n, 0) / total, 4) for n in cand_names}
        winner = max(fc, key=lambda k: fc[k])

        district_results.append({
            "id":          d["id"],
            "num_voters":  total,
            "winner":      winner,
            "vote_shares": vote_shares,
        })
        parliament_gerry[winner] = parliament_gerry.get(winner, 0) + 1
        national_fc    += fc
        national_total += total

    # ── National D'Hondt ──────────────────────────────────────────────────
    national_shares: Dict[str, float] = {
        n: round(national_fc.get(n, 0) / max(national_total, 1), 4)
        for n in cand_names
    }
    num_total_seats = len(districts_raw)
    parliament_prop  = _dhondt(national_shares, num_total_seats)

    # ── Distortion & gerrymander index ────────────────────────────────────
    distortion_vals = [
        abs(parliament_gerry.get(n, 0) / num_total_seats - national_shares.get(n, 0))
        for n in cand_names
    ]
    distortion = round(sum(distortion_vals) / max(len(distortion_vals), 1), 4)

    # Gerrymander index: how far from proportional is the leading party?
    leading         = max(parliament_gerry, key=lambda k: parliament_gerry[k])
    gerry_seat_pct  = parliament_gerry.get(leading, 0) / max(num_total_seats, 1)
    gerry_vote_pct  = national_shares.get(leading, 0)
    # Normalise to [0, 1]: 0 = seat% == vote%, 1 = seat% >> vote%
    gerrymander_index = round(
        max(0.0, min(1.0, (gerry_seat_pct - gerry_vote_pct) / max(gerry_vote_pct, 0.01))),
        4,
    )

    # Voter snapshot for the map (capped at 500 for performance)
    snap_voters = [
        {
            "id":        v["id"],
            "x":         voter_positions[v["id"]][0],
            "y":         voter_positions[v["id"]][1],
            "preferred": voter_preferred[v["id"]],
        }
        for v in voters[:500]
    ]

    return {
        "districts":              district_results,
        "voters":                 snap_voters,
        "parliament_gerrymander": parliament_gerry,
        "parliament_proportional": parliament_prop,
        "national_vote_share":    national_shares,
        "distortion":             distortion,
        "gerrymander_index":      gerrymander_index,
        "winner":                 leading,
        "candidates":             cand_names,
        "num_seats":              num_total_seats,
    }, 200


# ── Multi-winner compare endpoint ─────────────────────────────────────────────

def _multiwinner_compare_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /multiwinner_compare — STV, D'Hondt, SPAV, Phragmén, FPTP."""
    num_voters = max(50,  min(500, int(data.get("num_voters",  200))))
    ideology   = str(data.get("ideology",  "random"))
    seed       = int(data.get("seed",        42))
    num_seats  = max(2,  min(10,  int(data.get("num_seats",    5))))
    cand_specs = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
        {"name": "Dave",  "x": -0.2, "y":  0.5},
    ])[:8]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400
    if num_seats >= len(cand_specs):
        return {"error": "num_seats must be less than number of candidates"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # ── Build ballots ──────────────────────────────────────────────────────
    # Full rankings for STV
    rankings: List[List[str]] = []
    for v in voters:
        uid = v["id"]
        rankings.append(
            sorted(true_utilities[uid].keys(), key=lambda k: -true_utilities[uid][k])
        )

    # Approval ballots: approve candidates above own mean utility
    approval_ballots: List[List[str]] = []
    for v in voters:
        uid        = v["id"]
        u          = true_utilities[uid]
        threshold  = sum(u.values()) / max(len(u), 1)
        approved   = [c for c in cand_names if u.get(c, 0) > threshold]
        if not approved:                          # always approve at least 1st choice
            approved = [max(u, key=lambda k: u[k])]
        approval_ballots.append(approved)

    # First-choice vote shares for D'Hondt / FPTP
    first_choice: Counter[str] = Counter(r[0] for r in rankings if r)
    total_voters  = len(voters) or 1
    vote_shares   = {n: first_choice.get(n, 0) / total_voters for n in cand_names}

    # ── Run all methods ────────────────────────────────────────────────────
    stv_raw    = get_stv_result(rankings, num_seats, "droop")
    dhondt_raw = get_dhondt_winners(vote_shares, num_seats)
    spav_raw   = get_spav_result(approval_ballots, num_seats)
    phrag_raw  = get_phragmen_result(approval_ballots, num_seats)
    mes_raw    = get_equal_shares_result(approval_ballots, num_seats)
    top_n      = sorted(cand_names, key=lambda c: -first_choice.get(c, 0))[:num_seats]

    def _to_seat_dict(elected: List[str]) -> Dict[str, int]:
        d: Dict[str, int] = {c: 0 for c in cand_names}
        for c in elected:
            d[c] = d.get(c, 0) + 1
        return d

    dhondt_elected = [c for c, s in sorted(dhondt_raw.items(), key=lambda kv: -kv[1]) if s > 0]
    methods: Dict[str, Dict[str, Any]] = {
        "stv":          {"seats": _to_seat_dict(stv_raw["elected"]),   "elected": stv_raw["elected"]},
        "dhondt":       {"seats": dhondt_raw,                          "elected": dhondt_elected},
        "spav":         {"seats": _to_seat_dict(spav_raw["elected"]),  "elected": spav_raw["elected"]},
        "phragmen":     {"seats": _to_seat_dict(phrag_raw["elected"]), "elected": phrag_raw["elected"]},
        "equal_shares": {"seats": _to_seat_dict(mes_raw["elected"]),   "elected": mes_raw["elected"]},
        "fptp":         {"seats": _to_seat_dict(top_n),                "elected": top_n},
    }

    # Justified-representation axioms (approval-based) for each method's committee.
    for mdata in methods.values():
        mdata["justified_representation"] = check_justified_representation(
            approval_ballots, mdata["elected"], num_seats
        )

    # ── Distortion metrics ─────────────────────────────────────────────────
    prop_seats = _dhondt(vote_shares, num_seats)   # proportional reference

    for method_name, mdata in methods.items():
        seat_dict = mdata["seats"]
        dist_vals = [
            abs(seat_dict.get(c, 0) / num_seats - vote_shares.get(c, 0))
            for c in cand_names
        ]
        mdata["distortion"]          = round(sum(dist_vals) / max(len(dist_vals), 1), 4)
        mdata["seat_vs_votes"]       = {
            c: {
                "seats":     seat_dict.get(c, 0),
                "seat_pct":  round(seat_dict.get(c, 0) / num_seats, 4),
                "vote_pct":  round(vote_shares.get(c, 0), 4),
                "delta":     round(seat_dict.get(c, 0) / num_seats - vote_shares.get(c, 0), 4),
            }
            for c in cand_names
        }

    best_method  = min(methods, key=lambda m: methods[m]["distortion"])
    worst_method = max(methods, key=lambda m: methods[m]["distortion"])

    return {
        "methods":      methods,
        "vote_shares":  {n: round(vote_shares[n], 4) for n in cand_names},
        "proportional_reference": prop_seats,
        "num_seats":    num_seats,
        "candidates":   cand_names,
        "best_method":  best_method,
        "worst_method": worst_method,
    }, 200

