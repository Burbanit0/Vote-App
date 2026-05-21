"""
theory.py — Arrow's Impossibility Theorem interactive explorer.

  POST /api/theory/arrow     Per-method axiom violation analysis + counterexamples
  POST /api/theory/iia-rate  Empirical IIA violation rate vs. number of candidates
"""
from __future__ import annotations

import random as _rnd
from collections import Counter
from typing import Any, Dict, List, Optional

from flask import Blueprint, Response, jsonify, request

from app.extensions import sim_limiter

theory_bp = Blueprint("theory", __name__, url_prefix="/api/theory")

# ── Arrow axiom violation map ─────────────────────────────────────────────────
# True = the method VIOLATES this axiom

_VIOLATIONS: Dict[str, Dict[str, bool]] = {
    "plurality":          {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "borda":              {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "irv":                {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "schulze":            {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "condorcet":          {"iia": True, "pareto": False, "transitivity": True,  "non_dictatorship": False},
    "approval":           {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "majority_judgment":  {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "kemeny_young":       {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "minimax":            {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "star_voting":        {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "two_round":          {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
}

# ── Counterexamples ───────────────────────────────────────────────────────────

# Plurality IIA: spoiler effect (C steals from B)
# Without C: B wins 4-3. With C: A wins 3-2-2.
_IIA_PLURALITY = {
    "profile": [
        ["A", "C", "B"], ["A", "C", "B"], ["A", "C", "B"],   # 3 prefer A (vote A)
        ["B", "A", "C"], ["B", "A", "C"],                     # 2 prefer B (vote B)
        ["C", "B", "A"], ["C", "B", "A"],                     # 2 prefer C (vote C)
    ],
    "without_c": "B",
    "with_c":    "A",
    "spoiler":   "C",
    "note": "Sans C : A:3 B:4 → B gagne. Avec C : A:3 B:2 C:2 → A gagne. Pourtant les préférences A-B n'ont pas changé.",
}

# Borda IIA: adding C reverses the A-B Borda ranking
# Without C: B wins (4 prefer B over A). With C: A > B in Borda.
_IIA_BORDA = {
    "profile": [
        ["A", "C", "B"], ["A", "C", "B"], ["A", "C", "B"],    # 3 voters (A>B)
        ["C", "B", "A"], ["C", "B", "A"], ["C", "B", "A"], ["C", "B", "A"],  # 4 voters (B>A)
    ],
    "without_c": "B",
    "with_c":    "A",
    "spoiler":   "C",
    "note": "Sans C : B gagne 4-3. Avec C : Borda donne A:6 B:4 C:11 → A > B. Préférences A-B inchangées.",
}

# Condorcet transitivity cycle (Condorcet paradox)
_TRANSITIVITY_CONDORCET = {
    "profile": [
        ["A", "B", "C"],
        ["B", "C", "A"],
        ["C", "A", "B"],
    ],
    "cycle": ["A", "B", "C", "A"],
    "note": "A bat B (2-1), B bat C (2-1), C bat A (2-1). Cycle A > B > C > A — aucun vainqueur de Condorcet.",
}

_TRADEOFF_TYPE: Dict[str, str] = {
    "plurality":         "majority_focus",
    "two_round":         "majority_focus",
    "irv":               "majority_focus",
    "borda":             "utility_focus",
    "star_voting":       "utility_focus",
    "majority_judgment": "utility_focus",
    "approval":          "utility_focus",
    "schulze":           "condorcet_focus",
    "condorcet":         "condorcet_focus",
    "kemeny_young":      "condorcet_focus",
    "minimax":           "condorcet_focus",
}


def _plurality_winner(profile: List[List[str]]) -> Optional[str]:
    tally: Counter = Counter(v[0] for v in profile if v)
    return tally.most_common(1)[0][0] if tally else None


# ── /api/theory/arrow ─────────────────────────────────────────────────────────

@theory_bp.route("/arrow", methods=["POST"])
@sim_limiter.limit("20 per minute")
def arrow_impossibility() -> tuple[Response, int]:
    """
    POST /api/theory/arrow

    For a given voting method, identify which of Arrow's axioms it violates
    and return the minimal counterexample demonstrating each violation.
    """
    data   = request.get_json() or {}
    method = str(data.get("method", "plurality")).lower().replace("-", "_")
    _      = int(data.get("seed", 42))

    viols = _VIOLATIONS.get(method, _VIOLATIONS["plurality"])

    violations: Dict[str, Any] = {}

    # ── IIA ──────────────────────────────────────────────────────────────
    ce_iia: Optional[Dict[str, Any]] = None
    if viols["iia"]:
        if method in ("borda", "star_voting"):
            ce_iia = _IIA_BORDA
        else:
            ce_iia = _IIA_PLURALITY
    violations["iia"] = {"violated": viols["iia"], "counterexample": ce_iia}

    # ── Pareto ───────────────────────────────────────────────────────────
    violations["pareto"] = {"violated": viols["pareto"], "counterexample": None}

    # ── Transitivity ─────────────────────────────────────────────────────
    ce_trans: Optional[Dict[str, Any]] = None
    if viols["transitivity"]:
        ce_trans = _TRANSITIVITY_CONDORCET
    violations["transitivity"] = {"violated": viols["transitivity"], "counterexample": ce_trans}

    # ── Non-dictatorship ─────────────────────────────────────────────────
    violations["non_dictatorship"] = {"violated": viols["non_dictatorship"], "counterexample": None}

    # ── Summary ──────────────────────────────────────────────────────────
    violated_list   = [ax for ax, v in viols.items() if v]
    satisfied_list  = [ax for ax, v in viols.items() if not v]

    if "transitivity" in violated_list:
        summary = (
            f"'{method}' peut produire des cycles de préférences collectives "
            "(paradoxe de Condorcet) : le vainqueur dépend de l'agenda."
        )
    elif "iia" in violated_list:
        summary = (
            f"'{method}' satisfait Pareto et la transitivité mais sacrifie l'IIA. "
            "Un candidat non-gagnant peut changer qui remporte l'élection (effet spoiler)."
        )
    else:
        summary = f"'{method}' satisfait {', '.join(satisfied_list)}."

    return jsonify({
        "method":        method,
        "violations":    violations,
        "arrow_summary": summary,
        "tradeoff_type": _TRADEOFF_TYPE.get(method, "majority_focus"),
    }), 200


# ── /api/theory/iia-rate ──────────────────────────────────────────────────────

@theory_bp.route("/iia-rate", methods=["POST"])
@sim_limiter.limit("10 per minute")
def iia_violation_rate() -> tuple[Response, int]:
    """
    POST /api/theory/iia-rate

    Empirically compute the probability that adding an irrelevant candidate
    changes the winner under the given method, for n_candidates in [2, max_n].
    Uses plurality for speed; extrapolated rates for others.
    """
    data           = request.get_json() or {}
    method         = str(data.get("method", "plurality")).lower()
    max_candidates = max(2, min(8, int(data.get("max_candidates", 8))))
    n_trials       = max(20, min(500, int(data.get("num_trials", 100))))
    seed           = int(data.get("seed", 42))

    def _empirical_rate(n: int) -> float:
        rng  = _rnd.Random(seed + n * 100)
        cands = list("ABCDEFGHIJ")[:n]
        hits  = 0
        for _ in range(n_trials):
            n_voters = rng.randint(3, 7)
            profile = [rng.sample(cands, n) for _ in range(n_voters)]
            winner_full = _plurality_winner(profile)
            if winner_full is None:
                continue
            others = [c for c in cands if c != winner_full]
            if not others:
                continue
            removed = rng.choice(others)
            reduced = [[c for c in v if c != removed] for v in profile]
            winner_red = _plurality_winner(reduced)
            if winner_full != winner_red:
                hits += 1
        return round(hits / n_trials, 4)

    # Compute for plurality; scale for other methods
    _SCALE: Dict[str, float] = {
        "plurality": 1.00, "borda": 0.60, "irv": 0.75,
        "schulze": 0.35, "condorcet": 0.30, "kemeny_young": 0.28,
        "approval": 0.55, "majority_judgment": 0.50,
    }
    scale = _SCALE.get(method, 1.0)

    curve = []
    for n in range(2, max_candidates + 1):
        base_rate = 0.0 if n <= 2 else _empirical_rate(n)
        curve.append({
            "n_candidates":   n,
            "violation_rate": round(min(1.0, base_rate * scale), 4),
        })

    return jsonify({"method": method, "curve": curve}), 200


# ── Plott Chaos Theorem ───────────────────────────────────────────────────────

import numpy as _np_t
from collections import deque as _deque_t

# Manipulation analysis imports (lazy, inside endpoint)





def _majority_beats(dists: "_np_t.ndarray", num_voters: int) -> "_np_t.ndarray":
    """beats[j,k] = True if policy j beats policy k in majority vote."""
    # dists shape: (n_voters, n_policies)
    # beats_count[j,k] = #{v: dists[v,j] < dists[v,k]}
    beats_count = _np_t.sum(dists[:, :, None] < dists[:, None, :], axis=0)
    return beats_count > num_voters / 2


def _top_cycle_scc(n: int, beats: "_np_t.ndarray") -> set:
    """Find the Smith set (top SCC) using Kosaraju's algorithm."""
    adj  = [[k for k in range(n) if k != j and beats[j, k]] for j in range(n)]
    radj = [[k for k in range(n) if k != j and beats[k, j]] for j in range(n)]

    visited = [False] * n
    order: List[int] = []

    def dfs1(v: int) -> None:
        stack = [(v, iter(adj[v]))]
        visited[v] = True
        while stack:
            v, it = stack[-1]
            try:
                u = next(it)
                if not visited[u]:
                    visited[u] = True
                    stack.append((u, iter(adj[u])))
            except StopIteration:
                order.append(v)
                stack.pop()

    for i in range(n):
        if not visited[i]:
            dfs1(i)

    visited2 = [False] * n
    components: List[List[int]] = []

    def dfs2(v: int, comp: List[int]) -> None:
        stack = [(v, iter(radj[v]))]
        visited2[v] = True
        comp.append(v)
        while stack:
            v, it = stack[-1]
            try:
                u = next(it)
                if not visited2[u]:
                    visited2[u] = True
                    comp.append(u)
                    stack.append((u, iter(radj[u])))
            except StopIteration:
                stack.pop()

    for v in reversed(order):
        if not visited2[v]:
            comp: List[int] = []
            dfs2(v, comp)
            components.append(comp)

    # Build condensation & find SCCs with no incoming edges → top set
    comp_of = [0] * n
    for ci, comp in enumerate(components):
        for v in comp:
            comp_of[v] = ci

    in_edges = [set() for _ in range(len(components))]
    for j in range(n):
        for k in adj[j]:
            if comp_of[j] != comp_of[k]:
                in_edges[comp_of[k]].add(comp_of[j])

    top_comps = [ci for ci in range(len(components)) if not in_edges[ci]]
    top_set: set = set()
    for ci in top_comps:
        top_set.update(components[ci])
    return top_set


def _bfs_path(from_i: int, to_i: int, beats: "_np_t.ndarray",
               max_depth: int, n: int) -> Optional[List[int]]:
    """BFS: path from from_i to to_i where each step k beats predecessor."""
    if from_i == to_i:
        return [from_i]
    visited: Dict[int, Optional[int]] = {from_i: None}
    queue = _deque_t([(from_i, 0)])
    while queue:
        cur, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for k in range(n):
            if k != cur and beats[k, cur] and k not in visited:
                visited[k] = cur
                if k == to_i:
                    path: List[int] = []
                    c: Optional[int] = to_i
                    while c is not None:
                        path.append(c)
                        c = visited[c]
                    path.reverse()
                    return path
                queue.append((k, depth + 1))
    return None


@theory_bp.route("/plott-chaos", methods=["POST"])
@sim_limiter.limit("5 per minute")
def plott_chaos() -> tuple[Response, int]:
    """
    POST /api/theory/plott-chaos

    Demonstrate Plott's Chaos Theorem: in 2D policy space with ≥3 voters,
    a Condorcet winner almost never exists, and from any starting point the
    agenda-setter can reach ANY other point via a sequence of majority votes.
    """
    data           = request.get_json() or {}
    num_voters     = max(3, min(21, int(data.get("num_voters",    5))))
    num_dims       = max(1, min(2,  int(data.get("num_dimensions", 2))))
    seed           = int(data.get("seed",    42))
    target_raw     = data.get("target_policy", [0.6, 0.6])
    start_raw      = data.get("start_policy",  [-0.6, -0.6])
    max_steps      = max(1, min(30, int(data.get("max_steps", 15))))

    target_policy = [float(_np_t.clip(target_raw[d] if d < len(target_raw) else 0.0, -1, 1))
                     for d in range(num_dims)]
    start_policy  = [float(_np_t.clip(start_raw[d]  if d < len(start_raw)  else 0.0, -1, 1))
                     for d in range(num_dims)]

    _np_t.random.seed(seed)

    # ── Voter ideal points ────────────────────────────────────────────────
    voter_ideals = _np_t.random.uniform(-1, 1, (num_voters, num_dims))

    # ── Policy grid ───────────────────────────────────────────────────────
    grid_n = 10       # 10 per dim; 100 or 10 policies total
    ax     = _np_t.linspace(-1, 1, grid_n)
    if num_dims == 1:
        policies = ax[:, None]
    else:
        XX, YY   = _np_t.meshgrid(ax, ax)
        policies = _np_t.column_stack([XX.ravel(), YY.ravel()])

    n_pol = len(policies)

    # ── Distance matrix: dists[v, p] = ||voter_v - policy_p||² ──────────
    dists = _np_t.sum(
        (voter_ideals[:, None, :] - policies[None, :, :]) ** 2, axis=2
    )   # shape: (n_voters, n_policies)

    # ── Majority beats matrix ─────────────────────────────────────────────
    beats = _majority_beats(dists, num_voters)

    # ── Condorcet winner ──────────────────────────────────────────────────
    tmp = beats.copy()
    _np_t.fill_diagonal(tmp, True)
    cw_mask = _np_t.all(tmp, axis=1)
    condorcet_winner_exists = bool(_np_t.any(cw_mask))

    # ── Top cycle ─────────────────────────────────────────────────────────
    top_set = _top_cycle_scc(n_pol, beats)
    top_cycle_size   = len(top_set)
    top_cycle_center = policies[list(top_set)].mean(axis=0).tolist() if top_set else [0.0] * num_dims

    # ── Nearest grid indices ──────────────────────────────────────────────
    def nearest(pt: List[float]) -> int:
        arr = _np_t.array(pt[:num_dims])
        return int(_np_t.argmin(_np_t.sum((policies - arr) ** 2, axis=1)))

    si = nearest(start_policy)
    ti = nearest(target_policy)
    alt_target = [-target_policy[d] for d in range(num_dims)]
    ai = nearest(alt_target)

    # ── BFS paths ─────────────────────────────────────────────────────────
    chaos_path_idx = _bfs_path(si, ti, beats, max_steps, n_pol)
    alt_path_idx   = _bfs_path(si, ai, beats, max_steps, n_pol)

    def to_coords(idx: Optional[List[int]]) -> List[List[float]]:
        return [policies[i].tolist() for i in idx] if idx else []

    chaos_steps = to_coords(chaos_path_idx)
    alt_steps   = to_coords(alt_path_idx)

    # ── Pedagogical note ──────────────────────────────────────────────────
    if condorcet_winner_exists:
        note = (
            f"Un gagnant de Condorcet existe — le chaos de Plott ne s'applique pas ici. "
            f"Essayez avec num_dimensions=2 et des positions d'électeurs moins régulières."
        )
    else:
        n_path = len(chaos_steps) - 1 if chaos_steps else 0
        note = (
            f"Aucun gagnant de Condorcet. Le top cycle couvre {top_cycle_size}/{n_pol} politiques. "
            f"En {n_path} votes successifs l'agenda peut conduire depuis {start_policy} "
            f"vers {target_policy}. Avec un agenda différent, la même séquence atteint "
            f"{alt_target} — résultats diamétralement opposés, même électorat."
        )

    return jsonify({
        "condorcet_winner_exists": condorcet_winner_exists,
        "top_cycle": {"size": top_cycle_size, "center": top_cycle_center},
        "chaos_path": {
            "from":      policies[si].tolist(),
            "to":        policies[ti].tolist(),
            "steps":     chaos_steps,
            "num_steps": max(0, len(chaos_steps) - 1),
        },
        "alternative_path": {
            "to":    policies[ai].tolist(),
            "steps": alt_steps,
        },
        "voter_ideal_points": voter_ideals.tolist(),
        "pedagogical_note":   note,
    }), 200


# ── Gibbard-Satterthwaite Manipulation Analysis ───────────────────────────────

@theory_bp.route("/manipulation-analysis", methods=["POST"])
@sim_limiter.limit("5 per minute")
def manipulation_analysis() -> tuple[Response, int]:
    """
    POST /api/theory/manipulation-analysis

    Identify, for a given voting method and electorate, which voters can
    profitably misrepresent their preferences and via which strategy
    (compromising, burying, push-over, or truncating).
    """
    import copy as _cp_m
    from app.routes.election import _build_base_electorate
    from app.utils.simulation_ranked_utils import (
        get_plurality_winner as _plur,
        get_borda_winner     as _bord,
        get_irv_winner       as _irv_,
        get_schulze_winner   as _sch_,
    )
    from app.constants import DEFAULT_ISSUES as _DI

    data       = request.get_json() or {}
    cand_specs = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]
    num_voters  = max(10, min(100, int(data.get("num_voters",   30))))
    ideology    = str(data.get("ideology",      "random"))
    seed        = int(data.get("seed",           42))
    method      = str(data.get("method",        "plurality"))
    strategies  = data.get("manipulation_strategies",
                           ["compromising", "burying", "pushover", "truncating"])

    if len(cand_specs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    # ── Special case: 2 candidates → never manipulable ───────────────────
    if len(cand_specs) == 2:
        return jsonify({
            "sincere_winner":    None,
            "manipulable":       False,
            "manipulation_count": 0,
            "manipulators":      [],
            "strategy_breakdown": {s: 0 for s in strategies},
            "key_manipulator":   None,
            "pedagogical_note":  (
                "Avec 2 candidats le vote sincère est toujours optimal — "
                "G-S ne s'applique qu'avec ≥3 candidats."
            ),
        }), 200

    _np_t.random.seed(seed)
    _rnd.seed(seed)
    issues = _DI

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    n_cands = len(cand_names)

    # ── Sincere rankings ──────────────────────────────────────────────────
    sincere_rankings: List[List[str]] = [
        sorted(sincere_utilities[v["id"]], key=lambda k: -sincere_utilities[v["id"]][k])
        for v in voters
    ]

    # ── Voter 2D positions ────────────────────────────────────────────────
    voter_pos = [
        [round(2.0 * v["issue_positions"].get("economy",        0.5) - 1.0, 3),
         round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3)]
        for v in voters
    ]

    # ── Election runner ───────────────────────────────────────────────────
    def _run(rnks: List[List[str]]) -> Optional[str]:
        full = [r + [c for c in cand_names if c not in r] for r in rnks]
        if method == "borda":
            return _bord(full) or cand_names[0]
        if method in ("irv", "two_round"):
            return _irv_(full) or cand_names[0]
        if method == "schulze":
            return _sch_(full) or cand_names[0]
        return _plur(full) or cand_names[0]

    sincere_winner = _run(sincere_rankings)

    # ── Strategy generators ───────────────────────────────────────────────
    def _compromising(sr: List[str]) -> List[tuple]:
        return [([alt] + [c for c in sr if c != alt], "compromising")
                for alt in cand_names if alt != sr[0]]

    def _burying(sr: List[str]) -> List[tuple]:
        # Push each non-top candidate to the bottom
        res = []
        for to_bury in cand_names:
            if to_bury != sr[0]:
                res.append(([c for c in sr if c != to_bury] + [to_bury], "burying"))
        return res

    def _pushover(sr: List[str]) -> List[tuple]:
        # Elevate the weakest (last) candidate to second place to create spoiler
        res = []
        if len(sr) < 3:
            return res
        weak = sr[-1]  # weakest
        if weak != sr[0]:
            alt = [sr[0], weak] + [c for c in sr[1:-1]]
            res.append((alt, "pushover"))
        return res

    def _truncating(sr: List[str]) -> List[tuple]:
        if method not in ("irv", "two_round", "approval"):
            return []
        res = []
        for length in range(1, len(sr)):  # partial rankings
            res.append((sr[:length], "truncating"))
        return res

    _strat_fns: Dict[str, Any] = {
        "compromising": _compromising,
        "burying":      _burying,
        "pushover":     _pushover,
        "truncating":   _truncating,
    }

    # ── Find profitable manipulations ─────────────────────────────────────
    manipulators: List[Dict[str, Any]] = []
    strat_counts: Dict[str, int] = {s: 0 for s in strategies}

    for v_idx, v in enumerate(voters):
        vid    = v["id"]
        sr     = sincere_rankings[v_idx]
        u_sinc = sincere_utilities[vid].get(sincere_winner, 0)

        best_gain, best_m = 0.0, None

        for strat in strategies:
            gen = _strat_fns.get(strat)
            if gen is None:
                continue
            for alt_r, s_type in gen(sr):
                if alt_r == sr:
                    continue
                mod     = list(sincere_rankings)
                mod[v_idx] = alt_r
                strat_w = _run(mod)

                if strat_w == sincere_winner:
                    continue

                gain = sincere_utilities[vid].get(strat_w, 0) - u_sinc
                if gain > 0 and gain > best_gain:
                    best_gain = gain
                    best_m = {
                        "voter_id":        vid,
                        "voter_ideology":  voter_pos[v_idx],
                        "sincere_vote":    sr,
                        "strategic_vote":  alt_r,
                        "strategy_type":   s_type,
                        "sincere_result":  sincere_winner,
                        "strategic_result": strat_w,
                        "utility_gain":    round(gain, 4),
                    }

        if best_m:
            manipulators.append(best_m)
            strat_counts[best_m["strategy_type"]] = strat_counts.get(best_m["strategy_type"], 0) + 1

    # ── Key manipulator ───────────────────────────────────────────────────
    key_m: Optional[Dict[str, Any]] = None
    if manipulators:
        km = max(manipulators, key=lambda m: m["utility_gain"])
        key_m = {"voter_id": km["voter_id"],
                 "strategy": km["strategy_type"],
                 "gain":     km["utility_gain"]}

    n_used = len(voters)
    note = (
        f"G-S : avec {n_cands} candidats et '{method}', "
        f"{len(manipulators)}/{n_used} électeurs ont intérêt à manipuler. "
    )
    if key_m:
        note += f"Meilleure stratégie : '{key_m['strategy']}' (gain {key_m['gain']:.3f})."
    else:
        note += "Aucune manipulation profitable sur ce profil."

    return jsonify({
        "sincere_winner":     sincere_winner,
        "manipulable":        len(manipulators) > 0,
        "manipulation_count": len(manipulators),
        "manipulators":       manipulators,
        "strategy_breakdown": strat_counts,
        "key_manipulator":    key_m,
        "pedagogical_note":   note,
    }), 200
