"""
api.domain.election.workers_dynamics — spatial-dynamics / equilibrium workers,
split out of the workers.py monolith (incremental decomposition).

Pure `data: dict -> (body, http_status)` workers: Hotelling-Downs equilibrium,
polarization, quadratic funding, affective polarization. Depends only on the
engine utils + the shared ._electorate / ._helpers.
"""
from __future__ import annotations

import math
import random as _random
from collections import Counter
from typing import Any, Dict, List, Optional  # noqa: F401

import numpy as _np

from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.simulation_metrics import compare_all_methods
from ._electorate import _build_base_electorate
from ._helpers import gini as _gini


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
    if N == 0 or C == 0:
        return 0.0

    score: float
    if method in ("plurality", "irv"):
        winners = utilities.argmax(axis=1)
        score = int((winners == cand_idx).sum()) / N

    elif method == "borda":
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

    else:
        winners = utilities.argmax(axis=1)
        score = int((winners == cand_idx).sum()) / N

    return score


def _hotelling_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /hotelling — extracted for FastAPI v2 reuse."""
    num_voters     = max(50,  min(500, int(data.get("num_voters",   200))))
    ideology       = str(data.get("ideology",   "random"))
    seed           = int(data.get("seed",         42))
    method         = str(data.get("method",     "plurality"))
    num_iterations = max(1,  min(20,  int(data.get("num_iterations", 10))))
    step_size      = max(0.01, min(0.15, float(data.get("step_size",   0.05))))
    cand_specs     = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    # ── Build fixed electorate ─────────────────────────────────────────────
    candidates, voters, _, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
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

        moved_any = False
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
                moved_any = True
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


def _winner_entropy(winners: List[Optional[str]]) -> float:
    """Normalised Shannon entropy of winner distribution ∈ [0, 1]."""
    valid = [w for w in winners if w]
    if not valid:
        return 1.0
    counts = Counter(valid)
    total  = len(valid)
    probs  = [c / total for c in counts.values()]
    import math as _math
    entropy = -sum(p * _math.log2(p) for p in probs if p > 0)
    max_e   = _math.log2(len(counts)) if len(counts) > 1 else 1.0
    return round(entropy / max_e if max_e > 0 else 0.0, 4)


def _polarization_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /polarization — extracted for FastAPI v2 reuse."""
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

    issues = DEFAULT_ISSUES
    results: List[Dict[str, Any]] = []

    for ideology in ideology_range:
        _random.seed(seed)
        _np.random.seed(seed)

        # ── Build reference electorate to compute polarization index ──────
        candidates, voters, true_utilities, cand_names = _build_base_electorate(
            cand_specs, num_voters, ideology, seed, issues
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
        global_winners:  List[Optional[str]] = []

        for sim_idx in range(num_simulations):
            sim_seed = seed + sim_idx + 1
            _random.seed(sim_seed)
            _np.random.seed(sim_seed)

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
                most_common_count = Counter(winners_this).most_common(1)[0][1]
                agreement_sum += most_common_count / len(winners_this)
                global_winners.append(Counter(winners_this).most_common(1)[0][0])
            else:
                global_winners.append(None)

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
        best_method  = min(avg_regrets, key=lambda k: avg_regrets[k]) if avg_regrets else ""
        worst_method = max(avg_regrets, key=lambda k: avg_regrets[k]) if avg_regrets else ""

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
    results_sorted = sorted(results, key=lambda r: r["polarization_index"])

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

    # 2. Most robust method under high polarization
    high_pol = [r for r in results_sorted if r["polarization_index"] > 0.2]
    if high_pol:
        all_best: Counter[str] = Counter(r["best_method"] for r in high_pol if r["best_method"])
        if all_best:
            robust = all_best.most_common(1)[0][0]
            # Compare to worst
            all_worst: Counter[str] = Counter(r["worst_method"] for r in high_pol if r["worst_method"])
            fragile = all_worst.most_common(1)[0][0] if all_worst else ""
            findings.append(
                f"{robust.capitalize()} est la méthode la plus robuste dans les "
                f"électorats polarisés — régret bayésien moyen inférieur à {fragile}."
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

def _quadratic_funding_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /quadratic-funding — extracted for FastAPI v2."""
    num_voters       = max(20,  min(500, int(data.get("num_voters",   100))))
    ideology         = str(data.get("ideology",   "random"))
    seed             = int(data.get("seed",         42))
    budget_per_voter = max(1.0, min(1000.0, float(data.get("budget_per_voter", 100.0))))
    matching_pool    = max(0.0, float(data.get("matching_pool", 10000.0)))
    projects_raw     = data.get("projects", [
        {"name": "Éducation",    "x": -0.4},
        {"name": "Santé",        "x":  0.0},
        {"name": "Infrastructure","x":  0.5},
        {"name": "Environnement","x": -0.6},
    ])
    projects_raw = projects_raw[:8]

    if len(projects_raw) < 2:
        return {"error": "At least 2 projects required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)

    project_names: List[str] = [str(p.get("name", f"Project {i}")) for i, p in enumerate(projects_raw)]
    project_xs:   List[float] = [max(-1.0, min(1.0, float(p.get("x", 0.0)))) for p in projects_raw]

    # ── Generate electorate ────────────────────────────────────────────────
    issues = DEFAULT_ISSUES
    dummy_cands = [
        {"name": f"_P{i}", "x": project_xs[i], "y": 0.0}
        for i in range(len(project_names))
    ]
    _, voters, true_utilities, _ = _build_base_electorate(
        dummy_cands, num_voters, ideology, seed, issues
    )
    # Map dummy candidate names back to project names
    proj_utilities: Dict[Any, Dict[str, float]] = {
        v["id"]: {project_names[j]: true_utilities[v["id"]][f"_P{j}"]
                  for j in range(len(project_names))}
        for v in voters
    }

    # ── Individual contributions (proportional to utility) ─────────────────
    # c_ip = utility(v,p) / Σ_p utility(v,p) * budget_per_voter
    contributions: Dict[str, float] = {p: 0.0 for p in project_names}

    # Per-voter, per-project contributions matrix (for QF)
    voter_contribs: List[Dict[str, float]] = []
    for v in voters:
        uid = v["id"]
        u   = proj_utilities[uid]
        total_u = sum(u.values()) or 1.0
        vc: Dict[str, float] = {}
        for p in project_names:
            c = u.get(p, 0.0) / total_u * budget_per_voter
            vc[p]               = c
            contributions[p]   += c
        voter_contribs.append(vc)

    total_private = sum(contributions.values()) or 1.0

    # ── QF allocation ──────────────────────────────────────────────────────
    qf_scores: Dict[str, float] = {}
    for p in project_names:
        sqrt_sum = sum(_np.sqrt(max(0.0, vc[p])) for vc in voter_contribs)
        qf_scores[p] = float(sqrt_sum ** 2)

    total_qf = sum(qf_scores.values()) or 1.0
    qf_matching: Dict[str, float] = {
        p: qf_scores[p] / total_qf * matching_pool for p in project_names
    }

    # ── 1P1V allocation ────────────────────────────────────────────────────
    vote_counts: Counter[str] = Counter()
    for v in voters:
        uid = v["id"]
        u   = proj_utilities[uid]
        fav = max(u, key=lambda k: u[k])
        vote_counts[fav] += 1

    n_voters = len(voters) or 1
    p1v1_matching: Dict[str, float] = {
        p: vote_counts.get(p, 0) / n_voters * matching_pool for p in project_names
    }

    # ── Proportional allocation ────────────────────────────────────────────
    prop_matching: Dict[str, float] = {
        p: contributions[p] / total_private * matching_pool for p in project_names
    }

    # ── Assemble project results ───────────────────────────────────────────
    projects_out: List[Dict[str, Any]] = []
    for p in project_names:
        priv = round(contributions[p], 2)
        mtch = round(qf_matching[p],   2)
        projects_out.append({
            "name":            p,
            "private_funding": priv,
            "matching":        mtch,
            "total":           round(priv + mtch, 2),
            "qf_score":        round(qf_scores[p], 2),
        })

    winner = max(project_names,
                 key=lambda p: contributions[p] + qf_matching[p])

    # Mechanism comparison (total funding under each mechanism)
    def _totals(matching_dict: Dict[str, float]) -> Dict[str, float]:
        return {p: round(contributions[p] + matching_dict[p], 2) for p in project_names}

    mechanism_comparison = {
        "1p1v":        _totals(p1v1_matching),
        "proportional": _totals(prop_matching),
        "qf":           _totals(qf_matching),
    }

    # Gini of total allocations under each mechanism
    gini_coefficients = {
        m: _gini(list(mechanism_comparison[m].values()))
        for m in ("1p1v", "proportional", "qf")
    }

    # Pedagogical note
    qf_winner   = max(project_names, key=lambda p: mechanism_comparison["qf"][p])
    prop_winner = max(project_names, key=lambda p: mechanism_comparison["proportional"][p])
    if qf_winner != prop_winner:
        note = (
            f"QF élit '{qf_winner}' (Gini={gini_coefficients['qf']:.2f}) "
            f"tandis que le proportionnel élit '{prop_winner}' "
            f"(Gini={gini_coefficients['proportional']:.2f}). "
            "QF amplifie les projets avec beaucoup de petits donateurs."
        )
    else:
        note = (
            f"Les trois mécanismes s'accordent sur '{qf_winner}'. "
            f"QF est tout de même plus égalitaire "
            f"(Gini QF={gini_coefficients['qf']:.2f} vs "
            f"proportionnel={gini_coefficients['proportional']:.2f})."
        )

    return {
        "projects":              projects_out,
        "winner":                winner,
        "mechanism_comparison":  mechanism_comparison,
        "gini_coefficients":     gini_coefficients,
        "vote_shares":           {p: round(vote_counts.get(p, 0) / n_voters, 4)
                                  for p in project_names},
        "matching_pool":         matching_pool,
        "budget_per_voter":      budget_per_voter,
        "pedagogical_note":      note,
    }, 200


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
            if c_camp == "centre" or v_camp == "centre" or c_camp == v_camp:
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
    """Pure worker for /affective-polarization — extracted for FastAPI v2."""
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

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
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
        _random.seed(s); _np.random.seed(s)
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
    _random.seed(seed); _np.random.seed(seed)
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

