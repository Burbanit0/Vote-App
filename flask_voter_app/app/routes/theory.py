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

# Manipulation analysis + judgment aggregation imports (lazy, inside endpoints)

# ── Judgment Aggregation Scenarios ────────────────────────────────────────────

_JA_SCENARIOS: Dict[str, Any] = {
    "legal": {
        "name": "Responsabilité contractuelle",
        "propositions": [
            {"text": "Le contrat existait",                        "type": "premise",     "id": "P1"},
            {"text": "Les obligations n'ont pas été remplies",     "type": "premise",     "id": "P2"},
            {"text": "Responsabilité contractuelle",               "type": "conclusion",  "id": "C"},
        ],
        # Each voter type is (P1, P2, C) — all individually coherent (C = P1 AND P2)
        "voter_types": [
            [True,  True,  True],   # both premises yes → responsible
            [True,  False, False],  # P1 yes, P2 no → no liability
            [False, True,  False],  # P1 no, P2 yes → no liability
        ],
        "type_weights": [1, 1, 1],
        # Constraints: (list_of_premise_ids, conclusion_id, rule)
        # rule = "AND_IMPLIES"     → if all premises T, conclusion must be T
        # rule = "ALL_IMPLIES_NOT" → if all premises T, conclusion must be F
        # rule = "NAND"            → not all (premises ∪ {conclusion}) can be T
        "constraints": [
            (["P1", "P2"], "C", "AND_IMPLIES"),
        ],
    },
    "budget": {
        "name": "Dilemme fiscal",
        "propositions": [
            {"text": "Il faut réduire la dette publique",                            "type": "premise",    "id": "P1"},
            {"text": "Il ne faut pas augmenter les impôts",                          "type": "premise",    "id": "P2"},
            {"text": "Il ne faut pas réduire les dépenses publiques",               "type": "premise",    "id": "P3"},
            {"text": "La situation fiscale est gérable sans sacrifice",              "type": "conclusion", "id": "C"},
        ],
        # C = NOT(P1 AND P2 AND P3) — can only be true if at least one concession is made
        "voter_types": [
            [True,  True,  False, True],   # can cut spending → manageable
            [True,  False, True,  True],   # can raise taxes → manageable
            [False, True,  True,  True],   # no debt problem → manageable
        ],
        "type_weights": [1, 1, 1],
        "constraints": [
            (["P1", "P2", "P3"], "C", "ALL_IMPLIES_NOT"),
        ],
    },
    "climate": {
        "name": "Dilemme climatique",
        "propositions": [
            {"text": "Le changement climatique est une urgence",                     "type": "premise",    "id": "P1"},
            {"text": "La croissance économique ne doit pas être sacrifiée",          "type": "premise",    "id": "P2"},
            {"text": "La taxation carbone freinerait significativement la croissance", "type": "premise",  "id": "P3"},
            {"text": "Il faut instaurer une taxe carbone",                           "type": "conclusion", "id": "C"},
        ],
        # NOT(P2 AND P3 AND C) — can't support growth + believe tax hurts + support tax
        "voter_types": [
            [True,  True,  False, True],   # urgency + growth + tax OK → tax carbon ✓
            [False, True,  True,  False],  # not urgent + growth + tax hurts → no tax ✓
            [True,  False, True,  True],   # urgency + growth sacrifice OK + tax hurts → tax anyway ✓
        ],
        "type_weights": [1, 1, 1],
        "constraints": [
            (["P2", "P3"], "C", "NAND"),   # can't have P2∧P3∧C simultaneously
        ],
    },
}







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


# ── Judgment Aggregation ──────────────────────────────────────────────────────

@theory_bp.route("/judgment-aggregation", methods=["POST"])
@sim_limiter.limit("10 per minute")
def judgment_aggregation() -> tuple[Response, int]:
    """
    POST /api/theory/judgment-aggregation

    Demonstrates the discursive dilemma (List & Pettit 2002):
    majority rule on propositions can produce collectively incoherent results
    even when every individual voter is perfectly coherent.
    """
    data       = request.get_json() or {}
    num_voters = max(1, min(100, int(data.get("num_voters", 12))))
    seed       = int(data.get("seed", 42))
    scenario   = str(data.get("scenario", "legal"))

    sc = _JA_SCENARIOS.get(scenario, _JA_SCENARIOS["legal"])
    props       = sc["propositions"]
    vtypes      = sc["voter_types"]
    weights     = sc["type_weights"]
    constraints = sc["constraints"]
    n_props     = len(props)

    # ── Index maps ────────────────────────────────────────────────────────
    id_to_idx = {p["id"]: i for i, p in enumerate(props)}

    # ── Sample voter types ────────────────────────────────────────────────
    total_w = sum(weights)
    cum_w   = [sum(weights[:k+1]) / total_w for k in range(len(weights))]

    rng = _rnd.Random(seed)
    voters_raw: List[List[bool]] = []
    for _ in range(num_voters):
        r = rng.random()
        t = next((i for i, c in enumerate(cum_w) if r < c), len(vtypes) - 1)
        voters_raw.append(list(vtypes[t]))

    # ── Majority votes ────────────────────────────────────────────────────
    yes_counts     = [sum(v[i] for v in voters_raw) for i in range(n_props)]
    yes_pcts       = [c / num_voters for c in yes_counts]
    collective: List[bool] = [pct > 0.5 for pct in yes_pcts]

    # ── Constraint check helper ───────────────────────────────────────────
    def _check(votes: List[bool], cstr: tuple) -> bool:
        """Return True if votes satisfy the constraint."""
        prem_ids, conc_id, rule = cstr
        p_vals = [votes[id_to_idx[pid]] for pid in prem_ids]
        c_val  = votes[id_to_idx[conc_id]]
        if rule == "AND_IMPLIES":
            return not (all(p_vals) and not c_val)   # all premises T → conclusion must be T
        if rule == "ALL_IMPLIES_NOT":
            return not (all(p_vals) and c_val)        # all premises T → conclusion must be F
        if rule == "NAND":
            return not (all(p_vals) and c_val)        # can't have all premises AND conclusion T
        return True

    # ── Individual coherence ──────────────────────────────────────────────
    coherent_count = sum(
        1 for v in voters_raw if all(_check(v, cstr) for cstr in constraints)
    )
    voter_coherence_rate = round(coherent_count / num_voters, 4) if num_voters else 1.0

    # ── Collective coherence ──────────────────────────────────────────────
    incoherences: List[Dict[str, Any]] = []
    for cstr in constraints:
        prem_ids, conc_id, rule = cstr
        if not _check(collective, cstr):
            p_vals = [collective[id_to_idx[pid]] for pid in prem_ids]
            c_val  = collective[id_to_idx[conc_id]]
            if rule == "AND_IMPLIES":
                problem = "Prémisses acceptées majoritairement, mais conclusion rejetée"
            elif rule == "ALL_IMPLIES_NOT":
                problem = "Toutes les prémisses acceptées, mais la conclusion les contredit"
            else:
                problem = "La conclusion est incompatible avec les prémisses acceptées"
            incoherences.append({
                "premises":    prem_ids,
                "conclusion":  conc_id,
                "problem":     problem,
            })

    collective_coherent = len(incoherences) == 0
    paradox_severity    = round(len(incoherences) / max(1, len(constraints)), 4)

    # ── Resolution methods ────────────────────────────────────────────────
    premise_based: Dict[str, Any] = {}
    for prem_ids, conc_id, rule in constraints:
        p_vals = [collective[id_to_idx[pid]] for pid in prem_ids]
        if rule == "AND_IMPLIES":
            premise_based[conc_id] = all(p_vals)
        elif rule in ("ALL_IMPLIES_NOT", "NAND"):
            premise_based[conc_id] = not all(p_vals)

    conclusion_based: Dict[str, Any] = {}
    for prem_ids, conc_id, rule in constraints:
        c_val = collective[id_to_idx[conc_id]]
        conclusion_based["premise_override"] = not c_val if incoherences else c_val

    # ── Pedagogical note ──────────────────────────────────────────────────
    if not collective_coherent:
        note = (
            f"Paradoxe de List-Pettit : {len(incoherences)} incohérence(s) dans le vote "
            f"collectif alors que {round(voter_coherence_rate*100)}% des électeurs sont "
            f"individuellement cohérents. La procédure (prémisses d'abord vs conclusion) "
            f"détermine le résultat — la démocratie délibérative est fondamentalement "
            f"sensible à l'ordre des questions."
        )
    else:
        note = (
            f"Aucune incohérence sur ce profil — le paradoxe ne se manifeste pas toujours. "
            f"Il dépend de la distribution des préférences et de la structure logique "
            f"des propositions."
        )

    return jsonify({
        "scenario": scenario,
        "scenario_name": sc["name"],
        "propositions": [
            {
                "text":           props[i]["text"],
                "type":           props[i]["type"],
                "id":             props[i]["id"],
                "yes_pct":        round(yes_pcts[i], 4),
                "collective_vote": collective[i],
            }
            for i in range(n_props)
        ],
        "collective_coherent":    collective_coherent,
        "incoherences":           incoherences,
        "voter_coherence_rate":   voter_coherence_rate,
        "paradox_severity":       paradox_severity,
        "resolution_methods": {
            "premise_based":    premise_based,
            "conclusion_based": conclusion_based,
        },
        "pedagogical_note":       note,
    }), 200


# ── Apportionment Methods & Balinski-Young Theorem ───────────────────────────

import math as _math_ap


def _hamilton(votes: Dict[str, int], n: int) -> Dict[str, int]:
    total = sum(votes.values())
    if total == 0 or n == 0:
        return {p: 0 for p in votes}
    quotas = {p: v * n / total for p, v in votes.items()}
    seats  = {p: int(q) for p, q in quotas.items()}
    rem    = n - sum(seats.values())
    by_rem = sorted(((q - seats[p], p) for p, q in quotas.items()), key=lambda x: (-x[0], x[1]))
    for i in range(rem):
        seats[by_rem[i][1]] += 1
    return seats


def _jefferson(votes: Dict[str, int], n: int) -> Dict[str, int]:
    seats = {p: 0 for p in votes}
    for _ in range(n):
        best = max(votes, key=lambda p: votes[p] / (seats[p] + 1))
        seats[best] += 1
    return seats


def _webster(votes: Dict[str, int], n: int) -> Dict[str, int]:
    seats = {p: 0 for p in votes}
    for _ in range(n):
        best = max(votes, key=lambda p: votes[p] / (2 * seats[p] + 1))
        seats[best] += 1
    return seats


def _adams_m(votes: Dict[str, int], n: int) -> Dict[str, int]:
    seats = {p: 0 for p in votes}
    for _ in range(n):
        best = max(votes, key=lambda p: votes[p] / max(1, 2 * seats[p] - 1))
        seats[best] += 1
    return seats


def _huntington(votes: Dict[str, int], n: int) -> Dict[str, int]:
    nv = len(votes)
    if nv > n:
        return {p: 0 for p in votes}
    seats = {p: 1 for p in votes}
    for _ in range(n - nv):
        best = max(votes, key=lambda p: votes[p] / _math_ap.sqrt(seats[p] * (seats[p] + 1)))
        seats[best] += 1
    return seats


def _quota_violation(votes: Dict[str, int], seats: Dict[str, int], n: int) -> bool:
    total = sum(votes.values())
    if total == 0:
        return False
    return any(
        seats.get(p, 0) < _math_ap.floor(v * n / total) or
        seats.get(p, 0) > _math_ap.ceil(v * n / total)
        for p, v in votes.items()
    )


def _alabama_paradox(votes: Dict[str, int], fn: Any, n: int) -> bool:
    s1 = fn(votes, n)
    s2 = fn(votes, n + 1)
    return any(s2.get(p, 0) < s1.get(p, 0) for p in votes)


def _population_paradox(votes: Dict[str, int], fn: Any, n: int) -> bool:
    s0 = fn(votes, n)
    for p in votes:
        if votes[p] == 0:
            continue
        nv = dict(votes)
        nv[p] = int(votes[p] * 1.01) + 1
        sn = fn(nv, n)
        if sn.get(p, 0) < s0.get(p, 0):
            return True
    return False


_AP_METHODS: Dict[str, tuple] = {
    "hamilton":        (_hamilton,    "neutral",       "Quotient garanti, paradoxe d'Alabama possible"),
    "jefferson":       (_jefferson,   "large_parties", "Monotone, favorise les grands partis, peut violer quota sup."),
    "webster":         (_webster,     "neutral",       "Plus neutre, monotone, léger risque de violation quota"),
    "adams":           (_adams_m,     "small_parties", "Monotone, favorise les petits partis, peut violer quota inf."),
    "huntington_hill": (_huntington,  "neutral",       "Méthode géométrique (USA), monotone, biais faible petits partis"),
}


@theory_bp.route("/apportionment", methods=["POST"])
@sim_limiter.limit("10 per minute")
def apportionment() -> tuple[Response, int]:
    """
    POST /api/theory/apportionment

    Compare apportionment methods and demonstrate Balinski-Young impossibility:
    no method can simultaneously satisfy the quota rule, house monotonicity
    (Alabama paradox free), and population monotonicity.
    """
    data         = request.get_json() or {}
    parties_raw  = data.get("parties", [
        {"name": "A", "votes": 9000},
        {"name": "B", "votes": 7000},
        {"name": "C", "votes": 5000},
    ])[:10]
    num_seats    = max(2,  min(1000, int(data.get("num_seats",    10))))
    methods_req  = data.get("methods",         list(_AP_METHODS.keys()))
    find_paradox = bool(data.get("find_paradoxes", True))

    votes: Dict[str, int] = {p["name"]: max(1, int(p["votes"])) for p in parties_raw}

    results: Dict[str, Any] = {}
    for mname in methods_req:
        if mname not in _AP_METHODS:
            continue
        fn, favors, desc = _AP_METHODS[mname]
        seats    = fn(votes, num_seats)
        qv       = _quota_violation(votes, seats, num_seats)     if find_paradox else False
        alabama  = _alabama_paradox(votes, fn, num_seats)        if find_paradox else False
        pop_par  = _population_paradox(votes, fn, num_seats)     if find_paradox else False
        results[mname] = {
            "seats":              seats,
            "quota_violation":    qv,
            "alabama_paradox":    alabama,
            "population_paradox": pop_par,
            "new_state_paradox":  False,
            "favors":             favors,
            "description":        desc,
        }

    note = (
        f"Balinski-Young (1982) : sur {num_seats} sièges entre {len(votes)} partis, "
        f"AUCUNE méthode ne peut satisfaire simultanément le quotient strict, "
        f"la monotonie de la chambre et la monotonie de la population. "
        f"Hamilton respecte le quotient mais produit le paradoxe d'Alabama. "
        f"Les méthodes diviseur sont monotones mais peuvent violer le quotient."
    )

    return jsonify({
        "results":                  results,
        "balinski_young_summary":   (
            "Il est mathématiquement impossible de satisfaire simultanément "
            "(1) le quotient strict, (2) la monotonie de la chambre, "
            "(3) la monotonie de la population. "
            "Chaque méthode sacrifie l'une de ces propriétés."
        ),
        "impossible_to_avoid":      ["Quotient strict", "Monotonie chambre", "Monotonie population"],
        "pedagogical_note":         note,
    }), 200


# ── Sen's Impossibility of a Paretian Liberal ────────────────────────────────

_SEN_ALTS = ["x", "y", "z"]
_SEN_ALT_NAMES = {
    "x": "Personne 1 lit le livre",
    "y": "Personne 2 lit le livre",
    "z": "Personne ne lit le livre",
}


def _check_sen(pref1: List[str], pref2: List[str],
               sphere1: tuple, sphere2: tuple) -> Dict[str, Any]:
    """
    Check the Sen paradox for 2 voters, 3 alternatives.
    Returns liberal_outcome, pareto_outcome, conflict flag, explanation.
    """
    alts = _SEN_ALTS

    # ── Liberal order from private spheres ────────────────────────────────
    lib: Dict[tuple, bool] = {}   # (a, b): a ≻L b

    for (a, b), pref in [(sphere1, pref1), (sphere2, pref2)]:
        if pref.index(a) < pref.index(b):
            lib[(a, b)] = True
        else:
            lib[(b, a)] = True

    # Transitive closure
    changed = True
    while changed:
        changed = False
        for x in alts:
            for y in alts:
                for z in alts:
                    if x != y != z != x:
                        if lib.get((x, y)) and lib.get((y, z)) and not lib.get((x, z)):
                            lib[(x, z)] = True
                            changed = True

    # ── Pareto order ──────────────────────────────────────────────────────
    par: Dict[tuple, bool] = {}   # (a, b): a ≻P b

    for a in alts:
        for b in alts:
            if a != b:
                if pref1.index(a) < pref1.index(b) and pref2.index(a) < pref2.index(b):
                    par[(a, b)] = True

    # ── Conflict detection ────────────────────────────────────────────────
    conflict = False
    conflict_pair: Optional[tuple] = None
    for a in alts:
        for b in alts:
            if a != b and lib.get((a, b)) and par.get((b, a)):
                conflict = True
                conflict_pair = (a, b)
                break
        if conflict:
            break

    # ── Liberal winner ────────────────────────────────────────────────────
    lib_winner: Optional[str] = None
    for a in alts:
        if all(lib.get((a, b)) for b in alts if b != a):
            lib_winner = a
            break

    # ── Pareto winner (first non-dominated) ──────────────────────────────
    par_winner: Optional[str] = None
    for a in alts:
        dominated = any(par.get((b, a)) for b in alts if b != a)
        if not dominated:
            par_winner = a
            break

    explanation = ""
    if conflict and conflict_pair:
        a_c, b_c = conflict_pair
        explanation = (
            f"Libéralisme : {a_c} ≻ {b_c} (droit individuel). "
            f"Pareto : {b_c} ≻ {a_c} (consensus unanime). Contradiction !"
        )

    return {
        "liberal_outcome":  lib_winner or "indéfini",
        "pareto_outcome":   par_winner or "indéfini",
        "conflict":         conflict and bool(lib_winner) and bool(par_winner) and lib_winner != par_winner,
        "explanation":      explanation,
        "lib_order":        {str(k): v for k, v in lib.items()},
        "par_order":        {str(k): v for k, v in par.items()},
    }


@theory_bp.route("/sen-paradox", methods=["POST"])
@sim_limiter.limit("10 per minute")
def sen_paradox() -> tuple[Response, int]:
    """
    POST /api/theory/sen-paradox

    Demonstrates Sen's Impossibility of a Paretian Liberal (1970):
    no social choice rule can simultaneously satisfy Pareto efficiency
    and minimal individual liberalism.
    """
    data       = request.get_json() or {}
    num_voters = int(data.get("num_voters", 2))   # always 2 for Sen paradox
    seed       = int(data.get("seed", 42))
    rights_def = str(data.get("rights_definition", "liberal"))

    # ── Canonical example (Sen 1970, Lady Chatterley) ─────────────────────
    canon_pref1 = ["z", "x", "y"]   # prude : nobody > self > other
    canon_pref2 = ["x", "y", "z"]   # lewd  : person1 > self > nobody
    canon_s1    = ("x", "z")        # person 1 decides whether they read
    canon_s2    = ("y", "z")        # person 2 decides whether they read

    canon_res   = _check_sen(canon_pref1, canon_pref2, canon_s1, canon_s2)

    canon_example = {
        "name": "Exemple classique (Sen 1970 — Lady Chatterley)",
        "voters_preferences": [canon_pref1, canon_pref2],
        "private_spheres":    {"voter_1": list(canon_s1), "voter_2": list(canon_s2)},
        "liberal_outcome":    canon_res["liberal_outcome"],
        "pareto_outcome":     canon_res["pareto_outcome"],
        "conflict":           canon_res["conflict"],
        "explanation":        canon_res["explanation"],
    }

    # ── Random profile survey ─────────────────────────────────────────────
    import itertools as _iter
    all_perms   = list(_iter.permutations(_SEN_ALTS))
    sphere_opts = [(_SEN_ALTS[i], _SEN_ALTS[j])
                   for i in range(3) for j in range(3) if i != j]

    rng_s      = _rnd.Random(seed)
    n_trials   = 300
    n_paradox  = 0
    rand_examples: List[Dict[str, Any]] = []

    for trial in range(n_trials):
        p1  = list(rng_s.choice(all_perms))
        p2  = list(rng_s.choice(all_perms))
        sp1 = rng_s.choice(sphere_opts)
        sp2 = rng_s.choice(sphere_opts)
        res = _check_sen(p1, p2, sp1, sp2)
        if res["conflict"]:
            n_paradox += 1
            if len(rand_examples) < 2:
                rand_examples.append({
                    "name": f"Profil aléatoire #{trial + 1}",
                    "voters_preferences": [p1, p2],
                    "private_spheres":    {"voter_1": list(sp1), "voter_2": list(sp2)},
                    "liberal_outcome":    res["liberal_outcome"],
                    "pareto_outcome":     res["pareto_outcome"],
                    "conflict":           True,
                    "explanation":        res["explanation"],
                })

    paradox_frequency = round(n_paradox / n_trials, 4)
    paradox_exists    = canon_res["conflict"] or n_paradox > 0
    paradox_examples  = ([canon_example] if canon_res["conflict"] else []) + rand_examples

    # ── Resolution options ────────────────────────────────────────────────
    resolution_options = [
        {
            "name":     "Pareto prioritaire",
            "outcome":  "Efficacité collective garantie",
            "cost":     "Perte de liberté individuelle",
            "theorist": "Utilitarisme classique",
        },
        {
            "name":     "Libéralisme prioritaire",
            "outcome":  "Autonomie individuelle garantie",
            "cost":     "Peut produire des résultats sous-optimaux",
            "theorist": "Sen lui-même (résignation pragmatique)",
        },
        {
            "name":     "Restriction du domaine",
            "outcome":  "Paradoxe évité par contrainte des préférences",
            "cost":     "Qui décide quelles préférences sont admissibles ?",
            "theorist": "Gaertner (1979)",
        },
        {
            "name":     "Droits comme contraintes absolues",
            "outcome":  "Sphères privées respectées, Pareto appliqué ailleurs",
            "cost":     "Nécessite une définition précise des droits inviolables",
            "theorist": "Sugden (1978)",
        },
    ]

    note = (
        f"Sen (1970) prouve qu'il est impossible de satisfaire simultanément "
        f"Pareto et le libéralisme minimal. Sur {n_trials} profils aléatoires, "
        f"{round(paradox_frequency * 100, 1)}% produisent le paradoxe. "
        f"Ce résultat force à choisir entre efficacité collective et liberté individuelle."
    )

    return jsonify({
        "paradox_exists":      paradox_exists,
        "paradox_examples":    paradox_examples,
        "paradox_frequency":   paradox_frequency,
        "alternative_names":   _SEN_ALT_NAMES,
        "resolution_options":  resolution_options,
        "real_world_analogy":  (
            "Votre voisin préfère jouer de la musique la nuit (sa liberté). "
            "Vous préférez le silence. Ces préférences créent un conflit entre liberté "
            "individuelle et bien-être collectif qu'aucune règle simple ne résout entièrement."
        ),
        "pedagogical_note":    note,
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
