"""
api.domain.election.workers_dynamics — spatial-dynamics / equilibrium workers,
split out of the workers.py monolith (incremental decomposition).

Pure `data: dict -> (body, http_status)` workers: Hotelling-Downs equilibrium,
polarization, quadratic funding, affective polarization. Depends only on the
engine utils + the shared ._electorate / ._helpers.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from operator import itemgetter
from typing import Any, Dict, List, Mapping, Optional  # noqa: F401

import numpy as _np

from api.engine.utils.simulation_metrics import compare_all_methods
from ._electorate import _build_base_electorate, _build_electorate_from_seed
from ._helpers import modal_keys, reject_unknown_methods, tied_extremes


# ── Hotelling-Downs equilibrium ────────────────────────────────────────────────

def _hotelling_utility(
    voters_xy: _np.ndarray,      # shape (N, 2)
    cand_xy:   _np.ndarray,      # shape (C, 2)
) -> _np.ndarray:
    """
    Proximity-based utility matrix U[i, j] for voter i and candidate j.
    U = 1 - 0.5 * euclidean_distance / sqrt(2)  → ∈ [~0.3, 1.0]
    """
    diff = voters_xy[:, None, :] - cand_xy[None, :, :]   # (N, C, 2)
    dist = _np.sqrt((diff ** 2).sum(axis=2))              # (N, C)
    result: _np.ndarray = 1.0 - 0.5 * dist / _np.sqrt(2)
    return result


def _hotelling_score(
    utilities: _np.ndarray,   # (N, C) — utility matrix
    method:    str,
    cand_idx:  int,
) -> float:
    """
    Score for candidate cand_idx under the given method.
    Returns a continuous value in [0, 1] suitable for gradient ascent.
    """
    N, C = utilities.shape
    if 0 in (N, C):
        return 0.0

    score: float
    if method == "borda":
        ranks  = _np.argsort(-utilities, axis=1)
        points = _np.zeros((N, C))
        for k in range(C):
            points[_np.arange(N), ranks[:, k]] = C - 1 - k
        total_possible = N * (C - 1)
        score = int(points[:, cand_idx].sum()) / max(total_possible, 1)

    elif method == "approval":
        means    = utilities.mean(axis=1, keepdims=True)
        approved = utilities > means
        score = int(approved[:, cand_idx].sum()) / N

    else:   # plurality -- the worker has already rejected any other name
        winners = utilities.argmax(axis=1)
        score = int((winners == cand_idx).sum()) / N

    return score


#: The candidate objectives /hotelling can climb (no IRV: it has no smooth share).
HOTELLING_METHODS = ("plurality", "borda", "approval")


def _hotelling_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """/hotelling — Hotelling-Downs iterative best-response Nash equilibrium."""
    num_voters     = max(50,  min(500, int(data.get("num_voters",   200))))
    ideology       = str(data.get("ideology",   "random"))
    seed           = int(data.get("seed",         42))
    method         = str(data.get("method",     "plurality"))
    if err := reject_unknown_methods([method], HOTELLING_METHODS):
        return err
    num_iterations = max(1,  min(20,  int(data.get("num_iterations", 10))))
    step_size      = max(0.01, min(0.15, float(data.get("step_size",   0.05))))
    cand_specs     = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    # ── Build fixed electorate ─────────────────────────────────────────────
    candidates, voters, _, cand_names, issues = _build_electorate_from_seed(
        cand_specs, num_voters, ideology, seed
    )

    # Voter 2-D positions (fixed throughout)
    voters_xy = _np.array([
        [
            2.0 * v["issue_positions"].get("economy", 0.5) - 1.0,
            2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0,
        ]
        for v in voters
    ])  # (N, 2)

    # Initial candidate positions
    cand_xy = _np.array([
        [max(-1.0, min(1.0, float(s.get("x", 0.0)))),
         max(-1.0, min(1.0, float(s.get("y", 0.0))))]
        for s in cand_specs
    ])  # (C, 2)

    N = len(voters)
    C = len(cand_names)
    DIRS = _np.array([[step_size, 0], [-step_size, 0],
                      [0, step_size], [0, -step_size]])

    # ── Iterative Nash ─────────────────────────────────────────────────────
    iterations_out: list[Dict[str, Any]] = []
    converged_set: set[str] = set()

    for step in range(num_iterations):
        utilities = _hotelling_utility(voters_xy, cand_xy)

        scores: Dict[str, float] = {
            cand_names[j]: round(_hotelling_score(utilities, method, j), 4)
            for j in range(C)
        }

        # Record snapshot before moving
        iterations_out.append({
            "step":               step,
            "candidates":         [
                {"name": cand_names[j], "x": round(float(cand_xy[j, 0]), 4),
                 "y": round(float(cand_xy[j, 1]), 4)}
                for j in range(C)
            ],
            "scores":             scores,
            "converged_candidates": sorted(converged_set),
        })

        for j in range(C):
            if cand_names[j] in converged_set:
                continue

            current_score = _hotelling_score(utilities, method, j)
            best_score    = current_score
            best_delta    = _np.zeros(2)

            for delta in DIRS:
                new_pos = _np.clip(cand_xy[j] + delta, -1.0, 1.0)
                trial   = cand_xy.copy()
                trial[j] = new_pos
                trial_u  = _hotelling_utility(voters_xy, trial)
                s        = _hotelling_score(trial_u, method, j)
                if s > best_score + 1e-6:
                    best_score = s
                    best_delta = delta

            if _np.any(best_delta != 0):
                cand_xy[j] = _np.clip(cand_xy[j] + best_delta, -1.0, 1.0)
            else:
                converged_set.add(cand_names[j])

        if len(converged_set) == C:
            break

    # Final snapshot
    utilities = _hotelling_utility(voters_xy, cand_xy)
    final_scores = {
        cand_names[j]: round(_hotelling_score(utilities, method, j), 4)
        for j in range(C)
    }
    iterations_out.append({
        "step":               len(iterations_out),
        "candidates":         [
            {"name": cand_names[j], "x": round(float(cand_xy[j, 0]), 4),
             "y": round(float(cand_xy[j, 1]), 4)}
            for j in range(C)
        ],
        "scores":             final_scores,
        "converged_candidates": sorted(converged_set),
    })

    final_positions = iterations_out[-1]["candidates"]
    converged       = len(converged_set) == C
    convergence_step: Optional[int] = (
        next((i["step"] for i in iterations_out if len(i["converged_candidates"]) == C), None)
    )

    # Classify equilibrium type
    xs = [p["x"] for p in final_positions]
    spread = max(xs) - min(xs) if xs else 0
    if spread < 0.15:
        eq_type = "center_convergence"
    elif converged and spread >= 0.15:
        eq_type = "dispersed"
    else:
        eq_type = "unstable"

    # Voter snapshot (max 200 for performance)
    voter_snaps = [
        {
            "x": round(float(voters_xy[i, 0]), 3),
            "y": round(float(voters_xy[i, 1]), 3),
        }
        for i in range(min(200, N))
    ]

    return {
        "iterations":        iterations_out,
        "converged":         converged,
        "convergence_step":  convergence_step,
        "final_positions":   final_positions,
        "equilibrium_type":  eq_type,
        "voters":            voter_snaps,
        "candidates":        cand_names,
        "method":            method,
    }, 200


# ── Polarization endpoint ──────────────────────────────────────────────────────

def _esteban_ray_index(positions: List[float], n_bins: int = 20) -> float:
    """
    Esteban-Ray (1994) polarization index P = Σᵢ Σⱼ πᵢ² πⱼ |yᵢ - yⱼ|
    discretised into n_bins equal-width bins over [-1, 1].
    """
    if not positions:
        return 0.0

    bins     = _np.linspace(-1.0, 1.0, n_bins + 1)
    counts, _ = _np.histogram(positions, bins=bins)
    total    = counts.sum() or 1
    pi       = counts / total                          # bin proportions
    centres  = (bins[:-1] + bins[1:]) / 2.0           # bin centres

    p = 0.0
    for i in range(n_bins):
        if pi[i] == 0:
            continue
        for j in range(n_bins):
            if pi[j] == 0:
                continue
            p += float(pi[i] ** 2 * pi[j] * abs(centres[i] - centres[j]))
    return round(p, 6)


def _winner_entropy(weights: Mapping[str, float]) -> float:
    """Normalised Shannon entropy of a winner distribution ∈ [0, 1].

    Takes weights rather than a list of names: a simulation whose methods tie
    has no single winner, so it contributes 1/k to each of its k tied leaders
    instead of one arbitrary name (which used to be whichever method the rule
    table happened to list first).
    """
    total = sum(weights.values())
    if total <= 0:
        return 1.0
    probs  = [w / total for w in weights.values() if w > 0]
    import math as _math
    entropy = -sum(p * _math.log2(p) for p in probs)
    max_e   = _math.log2(len(probs)) if len(probs) > 1 else 1.0
    return round(entropy / max_e if max_e > 0 else 0.0, 4)


def _polarization_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """/polarization — Per-ideology Esteban-Ray index + method robustness scan."""
    num_voters     = max(50,  min(300, int(data.get("num_voters",   150))))
    seed           = int(data.get("seed", 42))
    num_simulations = max(5, min(50,  int(data.get("num_simulations", 20))))
    # Pydantic Optional[List[str]] may pass null — fall back to the default.
    ideology_range: List[str] = data.get("ideology_range") or [
        "centrist", "random", "left_skewed", "right_skewed", "polarized",
    ]
    cand_specs = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:4]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    results: List[Dict[str, Any]] = []

    for ideology in ideology_range:
        # ── Build reference electorate to compute polarization index ──────
        candidates, voters, true_utilities, cand_names, issues = _build_electorate_from_seed(
            cand_specs, num_voters, ideology, seed
        )

        economy_positions: List[float] = [
            float(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0)
            for v in voters
        ]
        pol_index = _esteban_ray_index(economy_positions)

        # ── Monte Carlo simulations ────────────────────────────────────────
        condorcet_count   = 0
        agreement_sum     = 0.0
        # Per-method: collect regrets and winner lists
        method_regrets:  Dict[str, List[float]] = {}
        method_winners:  Dict[str, List[Optional[str]]] = {}
        # Per-simulation winner weight: a tie splits its vote across the tied
        # leaders, so `winner_stability` no longer depends on rule-table order.
        global_winners:  Dict[str, float] = defaultdict(float)

        for sim_idx in range(num_simulations):
            sim_seed = seed + sim_idx + 1

            _, sim_voters, sim_utils, _ = _build_base_electorate(
                cand_specs, num_voters, ideology, sim_seed, issues
            )

            mc_result = compare_all_methods(
                sim_voters, candidates, issues,
                blank_vote=False,
                override_utilities=sim_utils,
            )

            cw = mc_result.get("condorcet_winner")
            if cw:
                condorcet_count += 1

            methods_data: Dict[str, Any] = mc_result.get("methods", {})

            # Agreement: fraction of methods electing the most common winner
            winners_this = [
                md.get("winner") for md in methods_data.values() if md.get("winner")
            ]
            if winners_this:
                counts_this = Counter(winners_this)
                leaders = modal_keys(counts_this)
                agreement_sum += max(counts_this.values()) / len(winners_this)
                for leader in leaders:
                    global_winners[leader] += 1 / len(leaders)

            for method_name, md in methods_data.items():
                if method_name not in method_regrets:
                    method_regrets[method_name]  = []
                    method_winners[method_name]  = []
                r = md.get("bayesian_regret")
                if r is not None:
                    method_regrets[method_name].append(float(r))
                method_winners[method_name].append(md.get("winner"))

        condorcet_rate  = round(condorcet_count / num_simulations, 4)
        agreement_rate  = round(agreement_sum / num_simulations, 4)
        winner_stability = _winner_entropy(global_winners)

        # Best/worst method by average Bayesian Regret
        avg_regrets: Dict[str, float] = {
            m: round(sum(v) / len(v), 6)
            for m, v in method_regrets.items() if v
        }
        best_method, worst_method = tied_extremes(avg_regrets)

        results.append({
            "ideology":          ideology,
            "polarization_index": pol_index,
            "condorcet_rate":    condorcet_rate,
            "agreement_rate":    agreement_rate,
            "winner_stability":  winner_stability,
            "best_method":       best_method,
            "worst_method":      worst_method,
            "method_regrets":    avg_regrets,
        })

    # ── Key findings ───────────────────────────────────────────────────────
    results_sorted = sorted(results, key=itemgetter("polarization_index"))

    findings: List[str] = []

    # 1. Condorcet threshold
    low_cw = [r for r in results_sorted if r["condorcet_rate"] < 0.5]
    if low_cw:
        threshold = low_cw[0]["polarization_index"]
        pct       = round((1 - low_cw[0]["condorcet_rate"]) * 100)
        findings.append(
            f"À partir de P ≈ {threshold:.2f}, le vainqueur de Condorcet disparaît "
            f"dans {pct}% des simulations."
        )

    # 3. Agreement drops
    if len(results_sorted) >= 2:
        first_agree = results_sorted[0]["agreement_rate"]
        last_agree  = results_sorted[-1]["agreement_rate"]
        if last_agree < first_agree - 0.1:
            delta = round((first_agree - last_agree) * 100, 1)
            findings.append(
                f"L'accord inter-méthodes chute de {delta} points de pourcentage "
                "entre l'électorat le moins et le plus polarisé."
            )

    if not findings:
        findings.append(
            "Les résultats montrent que la polarisation affecte la qualité "
            "démocratique mesurée par l'accord inter-méthodes et l'existence "
            "d'un vainqueur de Condorcet."
        )

    return {
        "results":      results,
        "key_findings": findings,
    }, 200


# ── Quadratic Funding endpoint ─────────────────────────────────────────────────



# ── Affective polarization endpoint ──────────────────────────────────────────

def _apply_affective(
    sincere_utilities: Dict[Any, Dict[str, float]],
    voter_camps:       Dict[Any, str],        # voter_id → "left" | "right" | "centre"
    candidate_camps:   Dict[str, str],        # cand_name → camp
    hostility:         float,
) -> Dict[Any, Dict[str, float]]:
    """
    Apply affective polarization: penalise candidates from the opposing camp.
    U_affective(v, c) =
        U_sincere(v, c)                          if c is in voter v's camp
        U_sincere(v, c) × (1 - hostility)        if c is in the opposing camp
    """
    affective: Dict[Any, Dict[str, float]] = {}
    for vid, utils in sincere_utilities.items():
        v_camp    = voter_camps.get(vid, "centre")
        new_utils = {}
        for cname, u in utils.items():
            c_camp = candidate_camps.get(cname, "centre")
            if "centre" in (c_camp, v_camp) or c_camp == v_camp:
                new_utils[cname] = u
            else:
                new_utils[cname] = u * (1.0 - hostility)
        affective[vid] = new_utils
    return affective


def _run_all_on_utilities(
    voters:     List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    issues:     List[str],
    utilities:  Dict[Any, Dict[str, float]],
) -> Dict[str, Any]:
    """Run compare_all_methods with pre-computed utilities."""
    return compare_all_methods(
        voters, candidates, issues,
        blank_vote=False,
        override_utilities=utilities,
    )


def _affective_polarization_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """/affective-polarization — Iyengar 2019: voters penalise candidates from the opposing
    political camp."""
    num_voters       = max(50,  min(500, int(data.get("num_voters",   200))))
    ideology         = str(data.get("ideology",    "random"))
    seed             = int(data.get("seed",          42))
    affect_hostility = max(0.0, min(1.0, float(data.get("affect_hostility", 0.5))))
    camp_threshold   = max(0.0, min(1.0, float(data.get("camp_threshold",   0.1))))
    num_simulations  = max(5,   min(50,  int(data.get("num_simulations",    20))))
    cand_specs       = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    candidates, voters, sincere_utilities, cand_names, issues = _build_electorate_from_seed(
        cand_specs, num_voters, ideology, seed
    )

    # ── Assign camps ──────────────────────────────────────────────────────
    def _x_pos(cand: Dict[str, Any]) -> float:
        val: float = round(2.0 * float(cand["ideology_position"]) - 1.0, 3)
        return val

    candidate_camps: Dict[str, str] = {}
    for c in candidates:
        x = _x_pos(c)
        if x < -camp_threshold:
            candidate_camps[c["name"]] = "left"
        elif x > camp_threshold:
            candidate_camps[c["name"]] = "right"
        else:
            candidate_camps[c["name"]] = "centre"

    voter_camps: Dict[Any, str] = {}
    for v in voters:
        uid      = v["id"]
        best     = max(sincere_utilities[uid], key=lambda k: sincere_utilities[uid][k])
        voter_camps[uid] = candidate_camps.get(best, "centre")

    # ── Affective utilities ────────────────────────────────────────────────
    affective_utilities = _apply_affective(
        sincere_utilities, voter_camps, candidate_camps, affect_hostility
    )

    # ── Run elections ──────────────────────────────────────────────────────
    sincere_mc  = _run_all_on_utilities(voters, candidates, issues, sincere_utilities)
    affective_mc = _run_all_on_utilities(voters, candidates, issues, affective_utilities)

    sincere_winners  = {m: md.get("winner") for m, md in sincere_mc.get("methods", {}).items()}
    affective_winners = {m: md.get("winner") for m, md in affective_mc.get("methods", {}).items()}

    sincere_cw  = sincere_mc.get("condorcet_winner")
    affective_cw = affective_mc.get("condorcet_winner")

    winner_changed = any(
        sincere_winners.get(m) != affective_winners.get(m)
        for m in sincere_winners
    )
    condorcet_violation = (sincere_cw != affective_cw)

    # ── Method sensitivity via Monte Carlo ─────────────────────────────────
    method_changes: Counter[str] = Counter()
    for sim_idx in range(num_simulations):
        s = seed + sim_idx + 1
        _, sv, su, _ = _build_base_electorate(cand_specs, num_voters, ideology, s, issues)
        vcamps = {}
        for v in sv:
            uid  = v["id"]
            best = max(su[uid], key=lambda k: su[uid][k])
            vcamps[uid] = candidate_camps.get(best, "centre")
        au = _apply_affective(su, vcamps, candidate_camps, affect_hostility)
        sm = _run_all_on_utilities(sv, candidates, issues, su)
        am = _run_all_on_utilities(sv, candidates, issues, au)
        for m in sm.get("methods", {}):
            if sm["methods"][m].get("winner") != am.get("methods", {}).get(m, {}).get("winner"):
                method_changes[m] += 1

    method_sensitivity = {
        m: round(method_changes.get(m, 0) / num_simulations, 4)
        for m in sincere_winners
    }

    # ── Affect curve (hostility 0 → 1 in 11 steps) ────────────────────────
    affect_curve: List[Dict[str, Any]] = []
    for step in range(11):
        h = round(step / 10, 1)
        au_step = _apply_affective(sincere_utilities, voter_camps, candidate_camps, h)
        mc_step = _run_all_on_utilities(voters, candidates, issues, au_step)
        methods_step = mc_step.get("methods", {})
        winners_step = [md.get("winner") for md in methods_step.values() if md.get("winner")]
        cw_exists    = mc_step.get("condorcet_winner") is not None
        if winners_step:
            most_common_count = Counter(winners_step).most_common(1)[0][1]
            agr = most_common_count / len(winners_step)
        else:
            agr = 0.0
        affect_curve.append({
            "hostility":      h,
            "condorcet_rate": 1.0 if cw_exists else 0.0,
            "agreement_rate": round(agr, 4),
        })

    # ── Voter snapshot for the map ─────────────────────────────────────────
    voter_snaps = [
        {
            "id":        v["id"],
            "x":         round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3),
            "y":         round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
            "camp":      voter_camps.get(v["id"], "centre"),
            "sincere_pref":   max(sincere_utilities[v["id"]], key=lambda k: sincere_utilities[v["id"]][k]),
            "affective_pref": max(affective_utilities[v["id"]], key=lambda k: affective_utilities[v["id"]][k]),
        }
        for v in voters[:300]
    ]

    # ── Pedagogical note ───────────────────────────────────────────────────
    changed_methods = [m for m in sincere_winners
                       if sincere_winners[m] != affective_winners[m]]
    if winner_changed:
        note = (
            f"La polarisation affective ({affect_hostility:.0%} d'hostilité) "
            f"change le vainqueur dans {len(changed_methods)} méthode(s) sur {len(sincere_winners)}. "
            f"Les méthodes les plus sensibles : {', '.join(sorted(changed_methods, key=lambda m: -method_sensitivity[m])[:3])}."
        )
    else:
        note = (
            f"Avec {affect_hostility:.0%} d'hostilité inter-partisane, "
            "aucune méthode ne change de vainqueur — "
            "l'électorat reste suffisamment consensuel pour résister à la polarisation affective."
        )

    return {
        "sincere_results":     sincere_winners,
        "affective_results":   affective_winners,
        "winner_changed":      winner_changed,
        "condorcet_violation": condorcet_violation,
        "sincere_cw":          sincere_cw,
        "affective_cw":        affective_cw,
        "method_sensitivity":  method_sensitivity,
        "affect_curve":        affect_curve,
        "candidate_camps":     candidate_camps,
        "voters":              voter_snaps,
        "candidates":          [{"name": c["name"], "x": _x_pos(c)} for c in candidates],
        "pedagogical_note":    note,
    }, 200

