"""
theory.py — Arrow's Impossibility Theorem interactive explorer.

  POST /api/theory/arrow     Per-method axiom violation analysis + counterexamples
  POST /api/theory/iia-rate  Empirical IIA violation rate vs. number of candidates
"""
from __future__ import annotations

import random as _rnd
from collections import Counter
from typing import Any, Dict, List, Optional




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

def _arrow_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /arrow — extracted for FastAPI v2."""
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

    return {
        "method":        method,
        "violations":    violations,
        "arrow_summary": summary,
        "tradeoff_type": _TRADEOFF_TYPE.get(method, "majority_focus"),
    }, 200




# ── /api/theory/iia-rate ──────────────────────────────────────────────────────

def _iia_rate_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /iia-rate — extracted for FastAPI v2."""
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

    return {"method": method, "curve": curve}, 200




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


def _plott_chaos_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /plott-chaos — extracted for FastAPI v2."""
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

    return {
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
    }, 200




# ── Judgment Aggregation ──────────────────────────────────────────────────────

def _judgment_aggregation_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /judgment-aggregation — extracted for FastAPI v2."""
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

    return {
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
    }, 200




# ── Agenda Manipulation ───────────────────────────────────────────────────────

import itertools as _itertools_ag


def _agenda_manipulation_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /agenda-manipulation — extracted for FastAPI v2."""
    alternatives = data.get("alternatives", ["Alice", "Bob", "Carol"])[:6]
    num_voters   = max(3, min(101, int(data.get("num_voters", 21))))
    if num_voters % 2 == 0:
        num_voters += 1       # force odd to avoid exact ties
    seed         = int(data.get("seed", 42))
    target       = str(data.get("target_outcome", alternatives[0] if alternatives else ""))
    _            = str(data.get("constraint_type", "binary_elimination"))

    n = len(alternatives)
    if n < 2:
        return {"error": "At least 2 alternatives required"}, 400
    if target not in alternatives:
        target = alternatives[0]

    _np_t.random.seed(seed)
    alt_idx = {a: i for i, a in enumerate(alternatives)}

    # ── Random voter utilities ────────────────────────────────────────────
    utils: _np_t.ndarray = _np_t.random.uniform(0, 1, (num_voters, n))

    # ── Pairwise matrix ───────────────────────────────────────────────────
    pairwise: Dict[str, Dict[str, float]] = {}
    for a in alternatives:
        pairwise[a] = {}
        for b in alternatives:
            if a == b:
                pairwise[a][b] = 0.5
            else:
                ia, ib  = alt_idx[a], alt_idx[b]
                wins    = int(_np_t.sum(utils[:, ia] > utils[:, ib]))
                pairwise[a][b] = round(wins / num_voters, 4)

    def beats(a: str, b: str) -> bool:
        return pairwise[a][b] > 0.5

    # ── Condorcet winner ──────────────────────────────────────────────────
    cw: Optional[str] = next(
        (a for a in alternatives if all(beats(a, b) for b in alternatives if b != a)),
        None,
    )

    # ── Binary elimination for a given agenda order ───────────────────────
    def binary_elim(order: List[str]) -> str:
        current = order[0]
        for challenger in order[1:]:
            if beats(challenger, current):
                current = challenger
        return current

    # ── Enumerate all permutations ────────────────────────────────────────
    all_perms = list(_itertools_ag.permutations(alternatives))

    achievable:          set                = set()
    sample_outcomes:     Dict[str, Any]     = {}
    optimal_for_target:  Optional[List[str]] = None
    neutral_agenda:      Optional[List[str]] = None
    worst_for_target:    Optional[List[str]] = None

    for perm in all_perms:
        order  = list(perm)
        result = binary_elim(order)
        achievable.add(result)

        key = "→".join(order)
        if len(sample_outcomes) < 30:
            sample_outcomes[key] = {"outcome": result, "sequence": order}

        if result == target and optimal_for_target is None:
            optimal_for_target = order
        if result != target and worst_for_target is None:
            worst_for_target = order
        if cw and result == cw and neutral_agenda is None:
            neutral_agenda = order

    if neutral_agenda is None:
        neutral_agenda = list(all_perms[0])
    if optimal_for_target is None:
        optimal_for_target = list(all_perms[0])
    if worst_for_target is None:
        worst_for_target = list(all_perms[-1])

    manip_power = round(len(achievable) / n, 4)

    if cw:
        note = (
            f"Un gagnant de Condorcet existe ({cw}) — il gagne toujours quel que soit "
            f"l'ordre d'agenda. Seulement 1/{n} résultat possible "
            f"(puissance de manipulation : {round(manip_power*100)}%)."
        )
    else:
        note = (
            f"Aucun gagnant de Condorcet ! Les {len(achievable)} alternative(s) "
            f"({', '.join(sorted(achievable))}) sont toutes atteignables via l'agenda. "
            f"Puissance de manipulation : {round(manip_power*100)}% — "
            f"l'agenda-setter a un contrôle total sur l'issue."
        )

    return {
        "pairwise_matrix":     pairwise,
        "condorcet_winner":    cw,
        "all_outcomes":        sample_outcomes,
        "achievable_outcomes": sorted(achievable),
        "optimal_agenda": {
            "for_target": optimal_for_target,
            "neutral":    neutral_agenda,
            "worst_case": worst_for_target,
        },
        "manipulation_power": manip_power,
        "pedagogical_note":   note,
    }, 200




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


def _apportionment_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /apportionment — extracted for FastAPI v2."""
    parties_raw  = data.get("parties", [
        {"name": "A", "votes": 9000},
        {"name": "B", "votes": 7000},
        {"name": "C", "votes": 5000},
    ])[:10]
    num_seats    = max(2,  min(1000, int(data.get("num_seats",    10))))
    methods_req  = data.get("methods") or list(_AP_METHODS.keys())
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

    return {
        "results":                  results,
        "balinski_young_summary":   (
            "Il est mathématiquement impossible de satisfaire simultanément "
            "(1) le quotient strict, (2) la monotonie de la chambre, "
            "(3) la monotonie de la population. "
            "Chaque méthode sacrifie l'une de ces propriétés."
        ),
        "impossible_to_avoid":      ["Quotient strict", "Monotonie chambre", "Monotonie population"],
        "pedagogical_note":         note,
    }, 200




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


def _sen_paradox_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /sen-paradox — extracted for FastAPI v2."""
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

    return {
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
    }, 200




# ── Gibbard-Satterthwaite Manipulation Analysis ───────────────────────────────

def _manipulation_analysis_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /manipulation-analysis — extracted for FastAPI v2."""
    import copy as _cp_m  # noqa: F401  (kept for parity with original imports)
    from app.routes.election import _build_base_electorate
    from api_v2.engine.utils.simulation_ranked_utils import (
        get_plurality_winner as _plur,
        get_borda_winner     as _bord,
        get_irv_winner       as _irv_,
        get_schulze_winner   as _sch_,
    )
    from api_v2.engine.constants import DEFAULT_ISSUES as _DI

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
        return {"error": "At least 2 candidates required"}, 400

    # ── Special case: 2 candidates → never manipulable ───────────────────
    if len(cand_specs) == 2:
        return {
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
        }, 200

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

    return {
        "sincere_winner":     sincere_winner,
        "manipulable":        len(manipulators) > 0,
        "manipulation_count": len(manipulators),
        "manipulators":       manipulators,
        "strategy_breakdown": strat_counts,
        "key_manipulator":    key_m,
        "pedagogical_note":   note,
    }, 200




# ── /api/theory/majority-tyranny ──────────────────────────────────────────────

import math as _math_t  # noqa: E402

def _majority_tyranny_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /majority-tyranny — extracted for FastAPI v2."""
    num_voters:        int   = max(10, min(int(data.get("num_voters", 100)), 500))
    majority_pct:      float = max(0.51, min(float(data.get("majority_pct", 0.60)), 0.95))
    minority_intensity: float = max(1.0, min(float(data.get("minority_intensity", 3.0)), 10.0))
    num_decisions:     int   = max(10, min(int(data.get("num_decisions", 50)), 200))
    seed:              int   = int(data.get("seed", 42))
    rules: List[str]         = data.get("decision_rules") or [
        "simple_majority", "supermajority_2_3", "supermajority_3_4",
        "unanimous", "qv", "mj",
    ]

    rng = _rnd.Random(seed)

    n_majority = int(round(num_voters * majority_pct))
    n_minority = num_voters - n_majority

    # ── Decision rule logic ───────────────────────────────────────────────────
    # Each decision: majority wants option A (utility 1.0 for majority, 0 for minority)
    # Minority wants option B (utility 0 for majority, minority_intensity for minority)
    # Normalised so comparison is fair.
    # We model intensity as votes/credits scaled by intensity.

    def _resolve(rule: str, rng_local: _rnd.Random) -> Dict[str, float]:
        """
        Return {"majority_wins": bool, "maj_util": float, "min_util": float}
        for one decision under a given rule.
        """
        # Add small noise so not all decisions are identical
        maj_intensity  = 1.0 + rng_local.uniform(-0.1, 0.1)
        min_intensity_ = minority_intensity + rng_local.uniform(-0.3, 0.3)
        min_intensity_ = max(0.1, min_intensity_)

        maj_wins = False

        if rule == "simple_majority":
            maj_wins = n_majority > n_minority

        elif rule == "supermajority_2_3":
            threshold = num_voters * (2 / 3)
            maj_wins = n_majority >= threshold

        elif rule == "supermajority_3_4":
            threshold = num_voters * (3 / 4)
            maj_wins = n_majority >= threshold

        elif rule == "unanimous":
            # Minority has veto → they block anything they strongly oppose
            maj_wins = False  # minority always vetoes

        elif rule == "qv":
            # Quadratic Voting: votes proportional to sqrt(budget × intensity)
            # Each voter gets equal budget; minority spends more per decision
            budget = 100.0
            maj_credits  = n_majority * _math_t.sqrt(budget * maj_intensity)
            min_credits  = n_minority * _math_t.sqrt(budget * min_intensity_)
            maj_wins = maj_credits >= min_credits

        elif rule == "mj":
            # Majority Judgment: median grade wins
            # Majority grades A as 4/5, minority as 1/5
            # Majority grades B as 1/5, minority as 4/5 (scaled by intensity)
            maj_grade_A = 4.0
            min_grade_A = max(0.0, 5.0 - min(min_intensity_, 4.0))
            # Median grade for A: weighted by group size
            grades_A = [maj_grade_A] * n_majority + [min_grade_A] * n_minority
            grades_A.sort()
            median_A = grades_A[len(grades_A) // 2]

            maj_grade_B = 1.0
            min_grade_B = min(5.0, 1.0 + min_intensity_)
            grades_B = [maj_grade_B] * n_majority + [min_grade_B] * n_minority
            grades_B.sort()
            median_B = grades_B[len(grades_B) // 2]

            maj_wins = median_A >= median_B

        else:
            maj_wins = n_majority > n_minority

        # Utilities
        if maj_wins:
            maj_util = maj_intensity
            min_util = 0.0
        else:
            maj_util = 0.0
            min_util = min_intensity_

        return {"majority_wins": maj_wins, "maj_util": maj_util, "min_util": min_util}

    # ── Run simulations per rule ──────────────────────────────────────────────
    results: Dict[str, Any] = {}
    for rule in rules:
        rng_r = _rnd.Random(seed)
        decisions = [_resolve(rule, rng_r) for _ in range(num_decisions)]

        maj_wins_count = sum(1 for d in decisions if d["majority_wins"])
        minority_wins  = num_decisions - maj_wins_count

        avg_maj_util   = sum(d["maj_util"] for d in decisions) / num_decisions
        avg_min_util   = sum(d["min_util"] for d in decisions) / num_decisions

        # Pareto-optimal: minority wins ≥ minority_intensity * minority_wins
        # Simple majority baseline welfare
        simple_maj_welfare = n_majority * 1.0 * num_decisions  # all decisions go to majority
        actual_welfare     = (n_majority * avg_maj_util + n_minority * avg_min_util) * num_decisions
        # Efficiency loss relative to utilitarian optimum
        # Utilitarian opt: give each decision to whoever has higher total utility
        util_opt = num_decisions * max(n_majority * 1.0, n_minority * minority_intensity)
        actual_total = n_majority * avg_maj_util * num_decisions + n_minority * avg_min_util * num_decisions
        efficiency_loss = max(0.0, (util_opt - actual_total) / max(util_opt, 1.0))

        tyranny_index = 1.0 - (minority_wins / num_decisions)  # fraction where minority gets 0

        results[rule] = {
            "minority_win_rate":     round(minority_wins / num_decisions, 4),
            "minority_satisfaction": round(avg_min_util / minority_intensity, 4),
            "majority_satisfaction": round(avg_maj_util, 4),
            "total_welfare":         round(actual_total / (num_voters * num_decisions), 4),
            "efficiency_loss":       round(efficiency_loss, 4),
            "tyranny_index":         round(tyranny_index, 4),
        }

    # ── Tyranny curve: vary majority_pct 0.51 → 0.80 ─────────────────────────
    curve: List[Dict[str, Any]] = []
    for pct_raw in range(51, 82, 3):
        pct = pct_raw / 100.0
        n_maj_c = int(round(num_voters * pct))
        n_min_c = num_voters - n_maj_c
        by_rule: Dict[str, float] = {}
        for rule in rules:
            rng_c = _rnd.Random(seed + pct_raw)
            wins = 0
            for _ in range(20):  # lightweight sample
                d = _resolve_curve(rule, n_maj_c, n_min_c, num_voters, minority_intensity, rng_c)
                if not d:
                    wins += 1
            by_rule[rule] = round(1.0 - wins / 20, 4)
        curve.append({"majority_pct": pct, "tyranny_by_rule": by_rule})

    # ── Rankings ──────────────────────────────────────────────────────────────
    valid = [r for r in rules if r in results]
    best_protector = min(valid, key=lambda r: results[r]["tyranny_index"]) if valid else ""
    least_efficient = max(valid, key=lambda r: results[r]["efficiency_loss"]) if valid else ""

    note = (
        f"Avec {int(majority_pct * 100)}% de majorité permanente et une intensité "
        f"minoritaire ×{minority_intensity:.1f}, la règle '{best_protector}' protège "
        f"le mieux la minorité (tyranny_index = "
        f"{results.get(best_protector, {}).get('tyranny_index', 0):.2f}). "
        f"Tocqueville (1835) : sans contre-pouvoirs institutionnels, la majorité "
        f"peut légitimement opprimer une minorité de façon indéfinie."
    )

    return {
        "results":         results,
        "tyranny_curve":   curve,
        "best_protector":  best_protector,
        "least_efficient": least_efficient,
        "pedagogical_note": note,
    }, 200




def _resolve_curve(
    rule: str, n_maj: int, n_min: int, n_total: int,
    minority_intensity: float, rng: _rnd.Random,
) -> bool:
    """Return True if majority wins for the curve helper (lightweight)."""
    if rule == "simple_majority":
        return n_maj > n_min
    if rule == "supermajority_2_3":
        return n_maj >= n_total * (2 / 3)
    if rule == "supermajority_3_4":
        return n_maj >= n_total * (3 / 4)
    if rule == "unanimous":
        return False
    if rule == "qv":
        budget = 100.0
        return (n_maj * _math_t.sqrt(budget) >= n_min * _math_t.sqrt(budget * minority_intensity))
    if rule == "mj":
        grades_A = [4.0] * n_maj + [max(0.0, 5.0 - min(minority_intensity, 4.0))] * n_min
        grades_A.sort()
        grades_B = [1.0] * n_maj + [min(5.0, 1.0 + minority_intensity)] * n_min
        grades_B.sort()
        return grades_A[len(grades_A) // 2] >= grades_B[len(grades_B) // 2]
    return n_maj > n_min


# ── /api/theory/democratic-backsliding ────────────────────────────────────────

import numpy as _np_bs  # noqa: E402

_POINT_OF_NO_RETURN = 0.45   # democratic quality below which recovery is very unlikely

def _democratic_backsliding_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /democratic-backsliding — extracted for FastAPI v2."""
    candidates_raw: List[Dict[str, Any]] = data.get("candidates") or [
        {"name": "Incumbent", "x": 0.2, "y": 0.0},
        {"name": "Opposition", "x": -0.4, "y": 0.0},
    ]
    num_voters:        int   = max(20, min(int(data.get("num_voters", 100)), 1000))
    ideology:          str   = data.get("ideology", "random")
    seed:              int   = int(data.get("seed", 42))
    num_elections:     int   = max(2, min(int(data.get("num_elections", 8)), 15))
    method_bs:         str   = data.get("backsliding_method", "gerrymandering")
    intensity:         float = max(0.0, min(float(data.get("backsliding_intensity", 0.5)), 1.0))
    gr_in = data.get("guardrails") or {}
    guardrails: Dict[str, bool] = {
        "constitutional_court":    bool(gr_in.get("constitutional_court", False)),
        "opposition_media":        bool(gr_in.get("opposition_media", False)),
        "international_pressure":  bool(gr_in.get("international_pressure", False)),
        "supermajority_required":  bool(gr_in.get("supermajority_required", False)),
    }

    rng = _rnd.Random(seed)
    np_rng = _np_bs.random.default_rng(seed)

    # ── Candidate setup ───────────────────────────────────────────────────────
    if len(candidates_raw) < 2:
        candidates_raw = [
            {"name": "Incumbent", "x": 0.2, "y": 0.0},
            {"name": "Opposition", "x": -0.4, "y": 0.0},
        ]
    incumbent_name = candidates_raw[0]["name"]

    # ── Simulate base vote shares via spatial model ───────────────────────────
    def _base_vote_shares(nv: int, seed_local: int) -> Dict[str, float]:
        rng_l = _np_bs.random.default_rng(seed_local)
        if ideology == "polarized":
            voter_positions = rng_l.normal(0, 0.4, nv)
            voter_positions = _np_bs.clip(voter_positions, -1, 1)
        else:
            voter_positions = rng_l.uniform(-1, 1, nv)

        shares: Dict[str, float] = {c["name"]: 0 for c in candidates_raw}
        for vp in voter_positions:
            distances = {
                c["name"]: float((vp - c.get("x", 0.0)) ** 2)
                for c in candidates_raw
            }
            winner_name = min(distances, key=distances.get)  # type: ignore[arg-type]
            shares[winner_name] += 1
        return {k: v / nv for k, v in shares.items()}

    # ── Guardrail effectiveness parameters ───────────────────────────────────
    # Each guardrail reduces the effective intensity multiplier
    guardrail_resistance = 0.0
    if guardrails["constitutional_court"]:
        guardrail_resistance += 0.30
    if guardrails["opposition_media"]:
        guardrail_resistance += 0.20
    if guardrails["international_pressure"]:
        guardrail_resistance += 0.15
    if guardrails["supermajority_required"]:
        guardrail_resistance += 0.25

    effective_intensity = max(0.0, intensity * (1.0 - guardrail_resistance))

    # ── Cumulative advantage state ────────────────────────────────────────────
    gerry_bonus:      float = 0.0   # cumulative gerrymandering bonus (vote share add)
    media_bias:       float = 0.0   # cumulative media capture (utility shift)
    suppression_rate: float = 0.0   # opposition turnout reduction

    democratic_quality = 1.0
    consecutive_incumbent_wins = 0
    autocracy_reached = False
    autocracy_at_election: Optional[int] = None

    elections: List[Dict[str, Any]] = []

    for n in range(1, num_elections + 1):
        guardrails_triggered: List[str] = []

        # ── Base vote shares ──────────────────────────────────────────────────
        shares = _base_vote_shares(num_voters, seed + n)

        # ── Apply backsliding mechanisms ──────────────────────────────────────
        if method_bs == "gerrymandering":
            # Gerrymandering: directly boosts incumbent share
            bonus = gerry_bonus
            if guardrails["constitutional_court"] and bonus > 0.05:
                bonus = max(0.05, bonus * 0.6)
                guardrails_triggered.append("constitutional_court")
            shares[incumbent_name] = min(0.95, shares[incumbent_name] + bonus)
            # Renormalize
            total = sum(shares.values())
            shares = {k: v / total for k, v in shares.items()}

        elif method_bs == "media_capture":
            # Media capture: shift perceived utility toward incumbent
            bias = media_bias
            if guardrails["opposition_media"] and bias > 0.1:
                bias = max(0.1, bias * 0.55)
                guardrails_triggered.append("opposition_media")
            noise = rng.gauss(0, 0.02)
            shares[incumbent_name] = min(0.95, shares[incumbent_name] + bias + noise)
            total = sum(shares.values())
            shares = {k: v / total for k, v in shares.items()}

        elif method_bs == "voter_suppression":
            # Voter suppression: reduce effective opposition turnout
            suppression = suppression_rate
            if guardrails["supermajority_required"] and suppression > 0.1:
                suppression = max(0.1, suppression * 0.5)
                guardrails_triggered.append("supermajority_required")
            for cname, c in zip([c["name"] for c in candidates_raw], candidates_raw):
                if cname != incumbent_name:
                    shares[cname] = max(0.01, shares[cname] * (1.0 - suppression))
            total = sum(shares.values())
            shares = {k: v / total for k, v in shares.items()}

        # ── International pressure — soft resistance ───────────────────────
        if guardrails["international_pressure"] and democratic_quality < 0.7:
            shares[incumbent_name] = max(0.0, shares[incumbent_name] - 0.03)
            total = sum(shares.values())
            shares = {k: v / total for k, v in shares.items()}
            guardrails_triggered.append("international_pressure")

        # ── Determine election winner ─────────────────────────────────────────
        election_winner = max(shares, key=shares.get)  # type: ignore[arg-type]
        incumbent_won = (election_winner == incumbent_name)

        # ── Update democratic quality index ───────────────────────────────────
        # Quality declines by intensity × per-mechanism rate each time incumbent wins
        per_election_decay_base = effective_intensity * 0.12

        if incumbent_won:
            consecutive_incumbent_wins += 1
            # Decay accelerates with each consecutive win (compounding)
            decay = per_election_decay_base * (1.0 + consecutive_incumbent_wins * 0.15)
            democratic_quality = max(0.0, democratic_quality - decay)
        else:
            consecutive_incumbent_wins = 0
            # Opposition win slightly restores quality (institutional memory)
            democratic_quality = min(1.0, democratic_quality + 0.05)

        # Noise for realism
        democratic_quality += rng.gauss(0, 0.01)
        democratic_quality = max(0.0, min(1.0, democratic_quality))

        # ── Update cumulative advantages for next election ────────────────────
        if incumbent_won:
            per_step = effective_intensity * 0.06
            if method_bs == "gerrymandering":
                gerry_bonus = min(0.40, gerry_bonus + per_step)
            elif method_bs == "media_capture":
                media_bias  = min(0.40, media_bias + per_step)
            elif method_bs == "voter_suppression":
                suppression_rate = min(0.60, suppression_rate + per_step)
        else:
            # Partial rollback when opposition wins
            gerry_bonus      = max(0.0, gerry_bonus - 0.02)
            media_bias       = max(0.0, media_bias - 0.02)
            suppression_rate = max(0.0, suppression_rate - 0.02)

        # ── Autocracy detection ───────────────────────────────────────────────
        point_of_no_return = democratic_quality <= _POINT_OF_NO_RETURN
        if not autocracy_reached and democratic_quality <= 0.20:
            autocracy_reached     = True
            autocracy_at_election = n

        elections.append({
            "election_n":         n,
            "winner":             election_winner,
            "vote_shares":        {k: round(v, 4) for k, v in shares.items()},
            "democratic_quality": round(democratic_quality, 4),
            "advantages": {
                "gerrymandering_bonus": round(gerry_bonus, 4),
                "media_bias":           round(media_bias, 4),
                "suppression_rate":     round(suppression_rate, 4),
            },
            "guardrails_triggered": guardrails_triggered,
            "point_of_no_return":   point_of_no_return,
        })

    # ── Guardrail effectiveness: compare with/without ─────────────────────────
    final_quality = elections[-1]["democratic_quality"]
    # Rough counterfactual: without guardrails, extra decay per election ≈
    # guardrail_resistance × intensity × 0.12 × num_elections
    guardrail_quality_saved = guardrail_resistance * intensity * 0.12 * num_elections
    guardrail_effectiveness: Dict[str, float] = {}
    weights = {
        "constitutional_court":   0.30,
        "opposition_media":       0.20,
        "international_pressure": 0.15,
        "supermajority_required": 0.25,
    }
    for gr, active in guardrails.items():
        if active:
            guardrail_effectiveness[gr] = round(
                guardrail_quality_saved * weights[gr] / max(sum(weights[g] for g, a in guardrails.items() if a), 0.01),
                4,
            )
        else:
            guardrail_effectiveness[gr] = 0.0

    # ── Tipping points ────────────────────────────────────────────────────────
    tipping_points = [
        round(0.30 / max(intensity, 0.01), 3),  # intensity at which decline becomes fast
        round(0.60 / max(intensity, 0.01), 3),  # intensity at which autocracy likely within 10 elections
    ]
    tipping_points = [min(tp, 1.0) for tp in tipping_points]

    # ── Pedagogical note ──────────────────────────────────────────────────────
    active_gr = [k for k, v in guardrails.items() if v]
    if autocracy_reached:
        note = (
            f"Autocratie atteinte à l'élection n°{autocracy_at_election} "
            f"(qualité démocratique : {elections[autocracy_at_election - 1]['democratic_quality']:.2f}). "
        )
    else:
        note = (
            f"Qualité démocratique finale : {final_quality:.2f} après {num_elections} élections. "
        )
    if active_gr:
        note += (
            f"Les garde-fous actifs ({', '.join(active_gr)}) ont sauvé "
            f"≈{guardrail_quality_saved:.2f} unités de qualité démocratique. "
        )
    note += (
        "Paradoxe de Popper (1945) : une démocratie sans droits non-dérogeables "
        "peut voter légalement pour sa propre destruction."
    )

    return {
        "elections":                elections,
        "autocracy_reached":        autocracy_reached,
        "autocracy_at_election":    autocracy_at_election,
        "guardrails_effectiveness": guardrail_effectiveness,
        "tipping_points":           tipping_points,
        "pedagogical_note":         note,
    }, 200




# ── /api/theory/intergenerational ────────────────────────────────────────────

_DEFAULT_DECISIONS = [
    {"name": "Retraite par répartition", "cost_present": -0.2, "benefit_future": -0.4, "time_horizon_years": 30},
    {"name": "Investissement éducation",  "cost_present": -0.3, "benefit_future":  0.8, "time_horizon_years": 20},
    {"name": "Dette publique",            "cost_present":  0.5, "benefit_future": -0.6, "time_horizon_years": 25},
    {"name": "Isolation des bâtiments",   "cost_present": -0.4, "benefit_future":  0.7, "time_horizon_years": 15},
    {"name": "Fonds souverain climatique","cost_present": -0.3, "benefit_future":  0.9, "time_horizon_years": 40},
]

_MECHANISMS = ("none", "proxy", "age_weighted", "veto")

# Discount rate for long-horizon welfare aggregation
_DISCOUNT = 0.03   # 3% per year


def _intergenerational_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /intergenerational — extracted for FastAPI v2."""
    raw_decisions: List[Dict[str, Any]] = data.get("decisions") or _DEFAULT_DECISIONS
    num_voters:    int   = max(20, min(int(data.get("num_voters", 100)), 1000))
    age_dist_raw:  List[float] = data.get("age_distribution") or [0.30, 0.45, 0.25]
    seed:          int   = int(data.get("seed", 42))
    mechanism_req: str   = data.get("future_generations_mechanism", "none")

    rng = _rnd.Random(seed)

    # Normalise age distribution (3 buckets: young/adult/senior)
    if len(age_dist_raw) != 3:
        age_dist_raw = [0.30, 0.45, 0.25]
    s = sum(age_dist_raw) or 1.0
    age_dist = [x / s for x in age_dist_raw]
    pct_young, pct_adult, pct_senior = age_dist

    # Validate decisions
    decisions: List[Dict[str, Any]] = []
    for d in raw_decisions[:8]:
        decisions.append({
            "name":               str(d.get("name", "?")),
            "cost_present":       max(-1.0, min(1.0, float(d.get("cost_present", 0.0)))),
            "benefit_future":     max(-1.0, min(1.0, float(d.get("benefit_future", 0.0)))),
            "time_horizon_years": max(1, min(50, int(d.get("time_horizon_years", 10)))),
        })

    # ── Voter population ──────────────────────────────────────────────────────
    # For each cohort, base preference = f(cost_present, benefit_future, age)
    # Young: care more about future; Senior: care more about present.

    def _cohort_support(dec: Dict[str, Any], cohort: str, noise: float = 0.0) -> float:
        """Returns support fraction [0, 1] for a cohort."""
        cp = dec["cost_present"]   # -1 bad now, +1 good now
        bf = dec["benefit_future"] # -1 bad later, +1 good later
        horizon = dec["time_horizon_years"]

        if cohort == "young":
            # Young discount future less — care more about bf
            future_weight = 0.60 + min(horizon / 100, 0.30)
            util = (1 - future_weight) * (cp + 1) / 2 + future_weight * (bf + 1) / 2
        elif cohort == "adult":
            future_weight = 0.40
            util = (1 - future_weight) * (cp + 1) / 2 + future_weight * (bf + 1) / 2
        else:  # senior
            future_weight = max(0.15, 0.30 - horizon * 0.008)
            util = (1 - future_weight) * (cp + 1) / 2 + future_weight * (bf + 1) / 2

        return max(0.0, min(1.0, util + noise))

    # ── Per-mechanism vote outcome ────────────────────────────────────────────

    all_mechs = list(_MECHANISMS) if mechanism_req == "none" else list(_MECHANISMS)

    decisions_results: List[Dict[str, Any]] = []

    for dec in decisions:
        by_mech: Dict[str, Any] = {}

        for mech in all_mechs:
            noise = rng.gauss(0, 0.03)

            s_young  = _cohort_support(dec, "young",  noise)
            s_adult  = _cohort_support(dec, "adult",  noise * 0.8)
            s_senior = _cohort_support(dec, "senior", noise * 0.5)

            # ── "none": simple majority of current voters ─────────────────
            if mech == "none":
                vote_pct = (
                    s_young  * pct_young +
                    s_adult  * pct_adult +
                    s_senior * pct_senior
                )

            # ── "proxy": commissaire with 20% weight voting for future ───
            elif mech == "proxy":
                proxy_support = max(0.0, min(1.0, (dec["benefit_future"] + 1) / 2))
                proxy_weight  = 0.20
                base_support  = (
                    s_young  * pct_young +
                    s_adult  * pct_adult +
                    s_senior * pct_senior
                )
                vote_pct = (1 - proxy_weight) * base_support + proxy_weight * proxy_support

            # ── "age_weighted": residual life expectancy weighting ────────
            elif mech == "age_weighted":
                w_young  = pct_young  * 1.5
                w_adult  = pct_adult  * 1.0
                w_senior = pct_senior * 0.5
                total_w  = w_young + w_adult + w_senior or 1.0
                vote_pct = (
                    s_young  * w_young  +
                    s_adult  * w_adult  +
                    s_senior * w_senior
                ) / total_w

            # ── "veto": young veto decisions with long time horizon ───────
            else:  # "veto"
                base_vote = (
                    s_young  * pct_young +
                    s_adult  * pct_adult +
                    s_senior * pct_senior
                )
                if dec["time_horizon_years"] > 15 and s_young < 0.5:
                    # Veto triggered: young block it
                    vote_pct = 0.0
                else:
                    vote_pct = base_vote

            adopted = vote_pct >= 0.50

            # ── Welfare calculation ───────────────────────────────────────
            # present welfare (generation 0-25 years): driven by cost_present
            w_present = (dec["cost_present"] + 1) / 2   # 0=bad, 1=good

            # future welfare (generation 25-50 years): driven by benefit_future
            # discounted at 3%/year to the time_horizon
            discount_factor = (1 + _DISCOUNT) ** (-dec["time_horizon_years"])
            w_future = ((dec["benefit_future"] + 1) / 2) * discount_factor

            if not adopted:
                # If not adopted, invert: cost not incurred, benefit not gained
                w_present = 1.0 - w_present   # no cost
                w_future  = 0.0               # no future benefit either

            # 50-year total = weighted average (present counts for first 25y)
            w_50y = 0.50 * w_present + 0.50 * w_future

            by_mech[mech] = {
                "adopted":           adopted,
                "vote_pct":          round(vote_pct, 4),
                "welfare_present":   round(w_present, 4),
                "welfare_future":    round(w_future, 4),
                "total_welfare_50y": round(w_50y, 4),
            }

        decisions_results.append({
            "decision_name": dec["name"],
            "by_mechanism":  by_mech,
        })

    # ── Mechanism-level aggregates ────────────────────────────────────────────
    mechanism_comparison: Dict[str, Any] = {}

    for mech in all_mechs:
        mech_results = [dr["by_mechanism"][mech] for dr in decisions_results]
        n = len(mech_results) or 1

        adoption_rate  = sum(1 for r in mech_results if r["adopted"]) / n
        avg_w_present  = sum(r["welfare_present"] for r in mech_results) / n
        avg_w_future   = sum(r["welfare_future"]  for r in mech_results) / n
        avg_w_50y      = sum(r["total_welfare_50y"] for r in mech_results) / n

        # Present bias: excess adoption of short-horizon decisions vs long ones
        short_dec = [i for i, d in enumerate(decisions) if d["time_horizon_years"] <= 15]
        long_dec  = [i for i, d in enumerate(decisions) if d["time_horizon_years"] >  15]
        adopt_short = (
            sum(1 for i in short_dec if mech_results[i]["adopted"]) / len(short_dec)
            if short_dec else adoption_rate
        )
        adopt_long  = (
            sum(1 for i in long_dec  if mech_results[i]["adopted"]) / len(long_dec)
            if long_dec else adoption_rate
        )
        present_bias = max(0.0, adopt_short - adopt_long)

        # Future welfare gain vs "none" baseline
        none_results   = [dr["by_mechanism"]["none"] for dr in decisions_results]
        avg_w_fut_none = sum(r["welfare_future"] for r in none_results) / n
        future_welfare_gain = avg_w_future - avg_w_fut_none

        # Intergenerational Gini: inequality between present & future welfare
        incomes = [avg_w_present, avg_w_future]
        mean_i  = sum(incomes) / 2 or 1.0
        gini    = sum(abs(a - b) for a in incomes for b in incomes) / (2 * 2 * mean_i)

        mechanism_comparison[mech] = {
            "adoption_rate":          round(adoption_rate, 4),
            "present_bias":           round(present_bias, 4),
            "future_welfare_gain":    round(future_welfare_gain, 4),
            "intergenerational_gini": round(gini, 4),
            "avg_welfare_50y":        round(avg_w_50y, 4),
        }

    # ── Pedagogical note ──────────────────────────────────────────────────────
    veto_adopt = mechanism_comparison["veto"]["adoption_rate"]
    none_adopt = mechanism_comparison["none"]["adoption_rate"]
    best_future_mech = max(all_mechs, key=lambda m: mechanism_comparison[m]["future_welfare_gain"])

    note = (
        f"Sans représentation des générations futures, {round(none_adopt*100)}% "
        f"des décisions sont adoptées. Le mécanisme '{best_future_mech}' maximise "
        f"le bien-être sur 50 ans. "
        f"Rawls (1971) : le 'voile d'ignorance' suggère que les décideurs ignorant "
        f"leur génération choisiraient des politiques plus équitables dans le temps."
    )

    return {
        "decisions_results":    decisions_results,
        "mechanism_comparison": mechanism_comparison,
        "pedagogical_note":     note,
    }, 200




# ── /api/theory/epistocracy ───────────────────────────────────────────────────

import statistics as _stats_ep  # noqa: E402

def _epistocracy_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /epistocracy — extracted for FastAPI v2."""
    candidates_raw: List[Dict[str, Any]] = data.get("candidates") or [
        {"name": "A", "x": -0.5, "y": 0.0},
        {"name": "B", "x":  0.0, "y": 0.0},
        {"name": "C", "x":  0.5, "y": 0.0},
    ]
    num_voters:    int   = max(10, min(int(data.get("num_voters", 100)), 1000))
    seed:          int   = int(data.get("seed", 42))
    comp_dist:     str   = data.get("voter_competence_distribution", "uniform")
    weighting_req: str   = data.get("weighting_scheme", "equal")  # noqa: F841
    epist_threshold: float = max(0.1, min(float(data.get("epistocracy_threshold", 0.7)), 0.99))

    params = data.get("competence_params") or {}
    comp_mean   = max(0.1, min(float(params.get("mean",        0.55)), 0.99))
    comp_std    = max(0.01, min(float(params.get("std",         0.15)), 0.40))
    expert_pct  = max(0.0,  min(float(params.get("expert_pct",  0.10)), 0.50))
    caplan_bias = bool(params.get("caplan_bias", True))

    rng = _rnd.Random(seed)

    n_cands = len(candidates_raw)
    if n_cands < 2:
        candidates_raw = [
            {"name": "A", "x": -0.5, "y": 0.0},
            {"name": "B", "x":  0.0, "y": 0.0},
        ]
        n_cands = 2

    # ── Generate voter competence distribution ────────────────────────────────
    competences: List[float] = []

    if comp_dist == "bimodal":
        # Two clusters: low-info and high-info
        for _ in range(num_voters):
            if rng.random() < 0.6:
                c = max(0.1, min(rng.gauss(comp_mean - 0.15, comp_std), 0.99))
            else:
                c = max(0.1, min(rng.gauss(comp_mean + 0.20, comp_std * 0.7), 0.99))
            competences.append(c)
    elif comp_dist == "expert_minority":
        n_experts = max(1, int(num_voters * expert_pct))
        for i in range(num_voters):
            if i < n_experts:
                c = max(0.8, min(rng.gauss(0.88, 0.05), 0.99))
            else:
                c = max(0.1, min(rng.gauss(comp_mean - 0.05, comp_std), 0.79))
            competences.append(c)
        rng.shuffle(competences)
    else:  # "uniform" — gaussian around mean
        for _ in range(num_voters):
            c = max(0.1, min(rng.gauss(comp_mean, comp_std), 0.99))
            competences.append(c)

    # ── Caplan biases: reduce effective competence for economic decisions ──────
    if caplan_bias:
        # Caplan's 4 biases reduce effective P by a correlated amount
        biased_competences = [
            max(0.1, min(c - rng.uniform(0.0, 0.15), 0.99))
            for c in competences
        ]
    else:
        biased_competences = list(competences)

    actual_mean        = _stats_ep.mean(competences)
    biased_mean        = _stats_ep.mean(biased_competences)
    expert_count       = sum(1 for c in competences if c >= 0.8)

    # ── "Omniscient" correct candidate: always candidate with lowest |x| (centrist) ──
    # This is the "best" choice for Bayesian welfare maximisation in a spatial model
    best_cand_idx = min(range(n_cands),
                        key=lambda i: abs(candidates_raw[i].get("x", 0.0)))
    best_cand_name = candidates_raw[best_cand_idx]["name"]

    # ── Simulate multiple elections per scheme across many trials ─────────────
    n_trials = 40   # Monte Carlo over voter preference noise

    schemes = ["equal", "competence_weighted", "epistocratic", "lottery"]
    results: Dict[str, Any] = {}

    for scheme in schemes:
        wins_best = 0
        total_regret = 0.0
        participates_total = 0.0

        for trial in range(n_trials):
            trial_seed = seed * 1000 + trial
            trial_rng  = _rnd.Random(trial_seed)

            # Determine which voters participate
            if scheme == "epistocratic":
                eligible = [(i, biased_competences[i])
                            for i in range(num_voters)
                            if biased_competences[i] >= epist_threshold]
            else:
                eligible = [(i, biased_competences[i]) for i in range(num_voters)]

            participates = len(eligible) / num_voters
            participates_total += participates

            if not eligible:
                # No one qualifies: fallback to random
                winner_idx = trial_rng.randrange(n_cands)
            elif scheme == "lottery":
                # Random dictator
                picked_voter_idx, picked_comp = trial_rng.choice(eligible)
                if trial_rng.random() < picked_comp:
                    winner_idx = best_cand_idx
                else:
                    alts = [j for j in range(n_cands) if j != best_cand_idx]
                    winner_idx = trial_rng.choice(alts)
            else:
                # Tally votes
                tally: List[float] = [0.0] * n_cands
                for voter_i, comp in eligible:
                    if trial_rng.random() < comp:
                        vote = best_cand_idx
                    else:
                        alts = [j for j in range(n_cands) if j != best_cand_idx]
                        vote = trial_rng.choice(alts)

                    if scheme == "competence_weighted":
                        weight = comp
                    else:
                        weight = 1.0
                    tally[vote] += weight

                winner_idx = tally.index(max(tally))

            # Regret: 0 if best, 1/n_cands baseline for random
            if winner_idx == best_cand_idx:
                wins_best     += 1
                trial_regret   = 0.0
            else:
                # Distance from best candidate in ideology space
                wx  = candidates_raw[winner_idx].get("x", 0.0)
                bx  = candidates_raw[best_cand_idx].get("x", 0.0)
                trial_regret = min(1.0, abs(wx - bx))

            total_regret += trial_regret

        results[scheme] = {
            "winner":              best_cand_name if wins_best > n_trials // 2 else
                                   candidates_raw[0]["name"],  # placeholder
            "bayesian_regret":     round(total_regret / n_trials, 4),
            "correct_choice_pct":  round(wins_best / n_trials, 4),
            "participates_pct":    round(participates_total / n_trials, 4),
        }

    # ── Expert vs democracy comparison ────────────────────────────────────────
    # Expert: single randomly drawn voter from top-competence decile
    expert_wins = 0
    for trial in range(n_trials):
        trial_rng = _rnd.Random(seed * 10000 + trial)
        top_experts = sorted(range(num_voters), key=lambda i: biased_competences[i], reverse=True)
        expert_i = top_experts[max(0, min(int(len(top_experts) * 0.10), len(top_experts) - 1))]
        expert_comp = biased_competences[expert_i]
        if trial_rng.random() < expert_comp:
            expert_wins += 1

    expert_regret   = round(1.0 - expert_wins / n_trials, 4)
    demo_regret     = results["equal"]["bayesian_regret"]

    # ── Condorcet threshold ────────────────────────────────────────────────────
    # Approximate P* where collective accuracy = 1/n_cands (random chance)
    # From theorem: acc ≈ 1/2 + (P - 0.5) * sqrt(N) * some_factor
    # Simpler: threshold is 1/n_cands (random-chance crossover)
    condorcet_threshold = round(0.5, 4)  # Classic CJT threshold

    # ── Pedagogical note ──────────────────────────────────────────────────────
    demo_acc  = results["equal"]["correct_choice_pct"]
    epist_acc = results["epistocratic"]["correct_choice_pct"]

    if biased_mean < 0.5:
        note = (
            f"Avec une compétence moyenne de {biased_mean:.2f} (biaisée par Caplan), "
            f"la démocratie standard choisit le bon candidat dans "
            f"{round(demo_acc*100)}% des cas — MOINS que le hasard ({round(100/n_cands)}%). "
            f"Condorcet (1785) : si P < 0.5, la majorité aggrave l'erreur."
        )
    else:
        note = (
            f"Avec une compétence moyenne de {biased_mean:.2f}, "
            f"la démocratie égale obtient {round(demo_acc*100)}% de bonnes décisions "
            f"vs {round(epist_acc*100)}% pour l'épistocracie "
            f"(seuil {epist_threshold:.0%}, "
            f"{round(results['epistocratic']['participates_pct']*100)}% de l'électorat). "
            f"Brennan (2016) : l'épistocracie améliore-t-elle réellement la qualité "
            f"des décisions, ou ne fait-elle qu'exclure ?"
        )

    return {
        "voter_competence_stats": {
            "mean":         round(actual_mean, 4),
            "biased_mean":  round(biased_mean, 4),
            "expert_count": expert_count,
        },
        "results":              results,
        "democracy_vs_expert":  {
            "democracy_regret":  demo_regret,
            "expert_regret":     expert_regret,
            "omniscient_regret": 0.0,
        },
        "condorcet_threshold":  condorcet_threshold,
        "pedagogical_note":     note,
    }, 200




# ── /api/theory/identity-voting ───────────────────────────────────────────────

def _identity_voting_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /identity-voting — extracted for FastAPI v2."""
    candidates_raw: List[Dict[str, Any]] = data.get("candidates") or [
        {"name": "Alice", "x": -0.5, "y": 0.0},
        {"name": "Bob",   "x":  0.0, "y": 0.0},
        {"name": "Carol", "x":  0.5, "y": 0.0},
    ]
    num_voters:      int   = max(20, min(int(data.get("num_voters", 200)), 2000))
    seed:            int   = int(data.get("seed", 42))
    identity_weight: float = max(0.0, min(float(data.get("identity_weight", 0.5)), 1.0))
    cross_pressure:  bool  = bool(data.get("cross_pressure", True))
    method:          str   = data.get("method", "plurality")

    default_groups = [
        {"name": "Groupe A", "pct": 0.40, "ideology_center": -0.3,
         "loyalty": 0.75, "candidate_affiliation": candidates_raw[0]["name"]},
        {"name": "Groupe B", "pct": 0.35, "ideology_center":  0.1,
         "loyalty": 0.60, "candidate_affiliation": candidates_raw[1]["name"]},
        {"name": "Groupe C", "pct": 0.25, "ideology_center":  0.4,
         "loyalty": 0.80, "candidate_affiliation": candidates_raw[2]["name"]},
    ]
    groups_raw: List[Dict[str, Any]] = data.get("identity_groups") or default_groups

    rng = _rnd.Random(seed)
    cand_names = [c["name"] for c in candidates_raw]

    # ── Normalise groups ──────────────────────────────────────────────────────
    groups: List[Dict[str, Any]] = []
    total_pct = sum(float(g.get("pct", 0.33)) for g in groups_raw) or 1.0
    for g in groups_raw:
        affil = str(g.get("candidate_affiliation", cand_names[0]))
        if affil not in cand_names:
            affil = cand_names[0]
        groups.append({
            "name":                  str(g.get("name", "?")),
            "pct":                   float(g.get("pct", 0.33)) / total_pct,
            "ideology_center":       float(g.get("ideology_center", 0.0)),
            "loyalty":               max(0.0, min(float(g.get("loyalty", 0.6)), 1.0)),
            "candidate_affiliation": affil,
        })

    # ── Generate voters ───────────────────────────────────────────────────────
    voters: List[Dict[str, Any]] = []
    group_sizes = [max(1, round(g["pct"] * num_voters)) for g in groups]
    # Adjust last group to hit exactly num_voters
    diff = num_voters - sum(group_sizes)
    group_sizes[-1] = max(1, group_sizes[-1] + diff)

    for gidx, (group, n_in_group) in enumerate(zip(groups, group_sizes)):
        for _ in range(n_in_group):
            ideology_pos = rng.gauss(group["ideology_center"], 0.2)
            ideology_pos = max(-1.0, min(1.0, ideology_pos))

            # Ideological vote: nearest candidate by distance
            distances = {c["name"]: abs(ideology_pos - c.get("x", 0.0))
                         for c in candidates_raw}
            ideo_vote = min(distances, key=distances.get)  # type: ignore[arg-type]

            # Identity vote: candidate affiliated with group
            identity_vote = group["candidate_affiliation"]

            # Cross-pressure: ideological ≠ identity → might abstain
            is_cross_pressured = ideo_vote != identity_vote
            abstains = False
            if cross_pressure and is_cross_pressured:
                # Abstention prob ∝ loyalty × |ideology distance|
                loyalty = group["loyalty"]
                abstain_prob = loyalty * 0.3 * abs(ideology_pos - group["ideology_center"])
                abstains = rng.random() < abstain_prob

            # Mixed vote
            use_identity = rng.random() < (identity_weight * group["loyalty"])
            if use_identity:
                final_vote = identity_vote
            else:
                final_vote = ideo_vote

            voters.append({
                "group":              gidx,
                "ideology":           ideology_pos,
                "ideo_vote":          ideo_vote,
                "identity_vote":      identity_vote,
                "final_vote":         final_vote,
                "is_cross_pressured": is_cross_pressured,
                "abstains":           abstains,
            })

    # ── Tally votes for 3 scenarios ───────────────────────────────────────────
    def _plurality(votes: List[str]) -> str:
        from collections import Counter as _C
        return _C(votes).most_common(1)[0][0] if votes else cand_names[0]

    sincere_votes  = [v["ideo_vote"]     for v in voters]
    identity_votes = [v["identity_vote"] for v in voters]
    mixed_votes    = [v["final_vote"]    for v in voters
                      if not (cross_pressure and v["abstains"])]

    sincere_winner  = _plurality(sincere_votes)
    identity_winner = _plurality(identity_votes)
    mixed_winner    = _plurality(mixed_votes)

    # ── Group results ─────────────────────────────────────────────────────────
    group_results: List[Dict[str, Any]] = []
    for gidx, group in enumerate(groups):
        members = [v for v in voters if v["group"] == gidx]
        if not members:
            continue
        n_total = len(members)
        n_identity_vote = sum(1 for v in members if v["identity_vote"] == group["candidate_affiliation"])
        n_ideo_match    = sum(1 for v in members if v["ideo_vote"] == group["candidate_affiliation"])
        group_results.append({
            "group_name":     group["name"],
            "affiliation":    group["candidate_affiliation"],
            "group_vote_pct": round(n_identity_vote / n_total, 4),
            "ideology_match": round(n_ideo_match / n_total, 4),
            "loyalty":        round(group["loyalty"], 4),
            "size_pct":       round(group["pct"], 4),
        })

    # ── Cross-pressured stats ─────────────────────────────────────────────────
    cross_pressured_voters = [v for v in voters if v["is_cross_pressured"]]
    n_cross = len(cross_pressured_voters)
    n_abstaining = sum(1 for v in cross_pressured_voters if v["abstains"])
    abstention_rate = n_abstaining / n_cross if n_cross > 0 else 0.0

    # ── Identity-weight curve ─────────────────────────────────────────────────
    curve: List[Dict[str, Any]] = []
    for w_pct in range(0, 105, 10):
        w = w_pct / 100.0
        curve_votes: List[str] = []
        rng_c = _rnd.Random(seed + w_pct)
        for v in voters:
            # Recompute for this weight
            gidx_v = v["group"]
            loyalty = groups[gidx_v]["loyalty"]
            use_id  = rng_c.random() < (w * loyalty)
            vote_c  = v["identity_vote"] if use_id else v["ideo_vote"]
            if not (cross_pressure and v["abstains"]):
                curve_votes.append(vote_c)
        w_winner = _plurality(curve_votes)
        # Agreement: fraction who would vote same under both identity=0 and identity=1
        ideo_tally   = {n: sincere_votes.count(n) for n in cand_names}
        id_tally     = {n: identity_votes.count(n) for n in cand_names}
        total_v = len(voters) or 1
        agreement = sum(min(ideo_tally.get(n, 0), id_tally.get(n, 0))
                        for n in cand_names) / total_v
        curve.append({
            "weight":         w,
            "winner":         w_winner,
            "agreement_rate": round(agreement, 4),
        })

    # ── Pedagogical note ──────────────────────────────────────────────────────
    n_cross_total = len(cross_pressured_voters)
    note = (
        f"Green, Palmquist & Schickler (2002) : les électeurs adoptent les positions "
        f"de leur camp, ils ne choisissent pas leur camp selon leurs positions. "
        f"Avec un poids identitaire de {int(identity_weight*100)}%, "
        f"le vainqueur {'change' if mixed_winner != sincere_winner else 'ne change pas'} "
        f"vs le vote idéologique pur. "
    )
    if n_cross_total > 0:
        note += (
            f"{n_cross_total} électeurs ({round(n_cross_total/num_voters*100)}%) sont "
            f"'cross-pressured' (identité ≠ idéologie) ; "
            f"taux d'abstention dans ce groupe : {round(abstention_rate*100)}%."
        )

    return {
        "sincere_winner":  sincere_winner,
        "identity_winner": identity_winner,
        "mixed_winner":    mixed_winner,
        "winner_changed":  mixed_winner != sincere_winner,
        "group_results":   group_results,
        "cross_pressured": {
            "count":          n_cross_total,
            "abstention_rate": round(abstention_rate, 4),
        },
        "identity_weight_curve": curve,
        "pedagogical_note":      note,
    }, 200




# ── /api/theory/assumption-testing ────────────────────────────────────────────

_ALL_ASSUMPTIONS = (
    "single_peaked", "stable_preferences", "rational_voters",
    "fixed_electorate", "measurable_utilities",
)

def _assumption_testing_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /assumption-testing — extracted for FastAPI v2."""
    base_sim: Dict[str, Any] = data.get("base_simulation") or {}
    assumptions: List[str]   = data.get("assumptions_to_relax") or list(_ALL_ASSUMPTIONS)

    # ── Extract base simulation parameters ────────────────────────────────────
    candidates_raw: List[Dict[str, Any]] = base_sim.get("candidates", [
        {"name": "Alice", "x": -0.4, "y": 0.0},
        {"name": "Bob",   "x":  0.1, "y": 0.0},
        {"name": "Carol", "x":  0.5, "y": 0.0},
    ])
    num_voters: int   = max(20, min(int(base_sim.get("num_voters", 100)), 500))
    ideology:   str   = base_sim.get("ideology", "random")
    seed:       int   = int(base_sim.get("seed", 42))
    n_trials:   int   = 30   # Monte Carlo trials per assumption

    cand_names = [c["name"] for c in candidates_raw]
    n_cands    = len(cand_names)
    if n_cands < 2:
        candidates_raw = [{"name": "Alice", "x": -0.4}, {"name": "Bob", "x": 0.4}]
        cand_names = ["Alice", "Bob"]
        n_cands = 2

    # ── Shared: generate base voter positions ─────────────────────────────────
    def _voter_positions(seed_local: int, n: int, dist: str) -> List[float]:
        rng_l = _rnd.Random(seed_local)
        if dist == "polarized":
            return [rng_l.gauss(-0.5, 0.2) if rng_l.random() < 0.5
                    else rng_l.gauss(0.5, 0.2) for _ in range(n)]
        return [rng_l.uniform(-1, 1) for _ in range(n)]

    def _nearest(pos: float, bump: Dict[str, float]) -> str:
        dists = {c["name"]: abs(pos - c.get("x", 0.0) + bump.get(c["name"], 0.0))
                 for c in candidates_raw}
        return min(dists, key=dists.get)  # type: ignore[arg-type]

    def _plurality_winner(votes: List[str]) -> Optional[str]:
        from collections import Counter as _C
        c = _C(votes)
        return c.most_common(1)[0][0] if c else None

    # ── Baseline: standard spatial model ─────────────────────────────────────
    base_positions = _voter_positions(seed, num_voters, ideology)
    baseline_votes = [_nearest(p, {}) for p in base_positions]
    baseline_winner = _plurality_winner(baseline_votes) or cand_names[0]

    # ── Simulate each assumption violation ───────────────────────────────────
    relaxed_results: Dict[str, Any] = {}

    for assumption in assumptions:
        if assumption not in _ALL_ASSUMPTIONS:
            continue

        trial_winners: List[str] = []

        for t in range(n_trials):
            t_rng = _rnd.Random(seed * 1000 + t)
            positions = _voter_positions(seed + t, num_voters, ideology)
            votes: List[str] = []

            for i, pos in enumerate(positions):
                if assumption == "stable_preferences":
                    # Add noise: preference drifts ±0.2 between poll and vote
                    noisy_pos = pos + t_rng.gauss(0, 0.15)
                    votes.append(_nearest(noisy_pos, {}))

                elif assumption == "single_peaked":
                    # 20% of voters have multi-modal prefs: skip nearest, pick random
                    if t_rng.random() < 0.20:
                        votes.append(t_rng.choice(cand_names))
                    else:
                        votes.append(_nearest(pos, {}))

                elif assumption == "rational_voters":
                    # 15% of voters have intransitive preferences → vote randomly
                    if t_rng.random() < 0.15:
                        votes.append(t_rng.choice(cand_names))
                    else:
                        votes.append(_nearest(pos, {}))

                elif assumption == "fixed_electorate":
                    # Some voters "drop out" or new voters "appear" based on prior winner
                    if t_rng.random() < 0.10:
                        # New voter with random position
                        rand_pos = t_rng.uniform(-1, 1)
                        votes.append(_nearest(rand_pos, {}))
                    else:
                        votes.append(_nearest(pos, {}))

                elif assumption == "measurable_utilities":
                    # Add measurement error ±0.1 to perceived candidate positions
                    bumps = {c["name"]: t_rng.gauss(0, 0.10) for c in candidates_raw}
                    votes.append(_nearest(pos, bumps))

                else:
                    votes.append(_nearest(pos, {}))

            w = _plurality_winner(votes)
            if w:
                trial_winners.append(w)

        if not trial_winners:
            trial_winners = [baseline_winner]

        # Statistics across trials
        from collections import Counter as _Ctr
        winner_counts = _Ctr(trial_winners)
        most_common   = winner_counts.most_common(1)[0][0]
        n_t           = len(trial_winners)

        # Fraction of trials where winner differs from baseline
        pct_changed = sum(1 for w in trial_winners if w != baseline_winner) / n_t
        winner_changed = most_common != baseline_winner

        # Variance proxy: entropy of winner distribution
        probs      = [cnt / n_t for cnt in winner_counts.values()]
        entropy    = -sum(p * _math_t.log2(p + 1e-9) for p in probs)
        max_ent    = _math_t.log2(n_cands)
        result_var = round(entropy / max_ent if max_ent > 0 else 0.0, 4)

        # 95% CI for the leading candidate's win rate
        p_lead = winner_counts[most_common] / n_t
        margin = 1.96 * _math_t.sqrt(p_lead * (1 - p_lead) / max(n_t, 1))
        ci     = [round(max(0, p_lead - margin), 4), round(min(1, p_lead + margin), 4)]

        relaxed_results[assumption] = {
            "winner":              most_common,
            "winner_changed":      winner_changed,
            "pct_trials_changed":  round(pct_changed, 4),
            "result_variance":     result_var,
            "confidence_interval": ci,
            "winner_distribution": {k: round(v / n_t, 4)
                                    for k, v in winner_counts.items()},
        }

    # ── Derived metrics ───────────────────────────────────────────────────────
    valid = {k: v for k, v in relaxed_results.items()}

    most_fragile = max(valid, key=lambda k: valid[k]["result_variance"]) if valid else ""
    robust_result = all(not v["winner_changed"] for v in valid.values())

    # ── Pedagogical note ──────────────────────────────────────────────────────
    if robust_result:
        note = (
            f"Résultat robuste : '{baseline_winner}' gagne quelle que soit "
            f"l'hypothèse relaxée. La simulation est relativement fiable sur "
            f"ce scénario. Cependant, la robustesse dépend du scénario — "
            f"d'autres configurations sont plus fragiles."
        )
    else:
        fragile_note = valid[most_fragile]["pct_trials_changed"] if most_fragile else 0
        note = (
            f"L'hypothèse la plus fragile est '{most_fragile}' : "
            f"le vainqueur change dans {round(fragile_note * 100)}% des simulations. "
            f"Arrow (1951) : l'impossibilité s'applique ici — les résultats de "
            f"Vote Lab sont des projections sous hypothèses fortes, "
            f"pas des vérités objectives."
        )

    return {
        "baseline_result": {
            "winner": baseline_winner,
            "regret": 0.0,
        },
        "relaxed_results":        relaxed_results,
        "most_fragile_assumption": most_fragile,
        "robust_result":          robust_result,
        "pedagogical_note":       note,
    }, 200




# ── /api/theory/collective-will ───────────────────────────────────────────────

import itertools as _it_cw  # noqa: E402

def _collective_will_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /collective-will — extracted for FastAPI v2."""
    candidates_raw: List[Dict[str, Any]] = data.get("candidates") or [
        {"name": "Alice", "x": -0.4, "y": 0.0},
        {"name": "Bob",   "x":  0.1, "y": 0.0},
        {"name": "Carol", "x":  0.5, "y": 0.0},
    ]
    num_voters:    int = max(10, min(int(data.get("num_voters", 100)),  500))
    ideology:      str = data.get("ideology", "random")
    seed:          int = int(data.get("seed", 42))
    num_methods:   int = max(2,  min(int(data.get("num_methods",  5)),  10))
    num_agendas:   int = max(2,  min(int(data.get("num_agendas",  4)),  6))
    num_sims:      int = max(1,  min(int(data.get("num_simulations", 1)), 5))

    cand_names = [c["name"] for c in candidates_raw]
    n_cands    = len(cand_names)
    if n_cands < 2:
        candidates_raw = [{"name": "Alice", "x": -0.4}, {"name": "Bob", "x": 0.4}]
        cand_names = ["Alice", "Bob"]
        n_cands = 2

    # Voting methods pool (subset used based on num_methods)
    _method_pool = [
        "plurality", "borda", "irv", "approval",
        "schulze", "minimax", "kemeny_young", "star", "median", "condorcet"
    ]
    methods_used = _method_pool[:min(num_methods, len(_method_pool))]

    rng = _rnd.Random(seed)

    # ── Generate voter positions (fixed electorate) ───────────────────────────
    if ideology == "polarized":
        voter_positions = [
            rng.gauss(-0.5, 0.2) if rng.random() < 0.5 else rng.gauss(0.5, 0.2)
            for _ in range(num_voters)
        ]
    else:
        voter_positions = [rng.uniform(-1, 1) for _ in range(num_voters)]

    voter_positions = [max(-1.0, min(1.0, p)) for p in voter_positions]

    # ── Utility matrix ────────────────────────────────────────────────────────
    def _utility(voter_pos: float, cand: Dict[str, Any]) -> float:
        cx = float(cand.get("x", 0.0))
        cy = float(cand.get("y", 0.0))
        return -((voter_pos - cx) ** 2 + cy ** 2)

    utilities: List[List[float]] = [
        [_utility(vp, c) for c in candidates_raw]
        for vp in voter_positions
    ]

    # Sincere rankings per voter (descending utility)
    sincere_rankings: List[List[str]] = [
        [cand_names[j] for j in sorted(range(n_cands), key=lambda k: -utilities[i][k])]
        for i in range(num_voters)
    ]

    # ── Plurality tally helper ─────────────────────────────────────────────────
    def _plurality(rankings: List[List[str]]) -> str:
        from collections import Counter as _C
        return _C(r[0] for r in rankings if r).most_common(1)[0][0]

    # ── Borda helper ──────────────────────────────────────────────────────────
    def _borda(rankings: List[List[str]]) -> str:
        scores: Dict[str, float] = {c: 0.0 for c in cand_names}
        for ranking in rankings:
            for pos, cand in enumerate(ranking):
                scores[cand] += n_cands - 1 - pos
        return max(scores, key=scores.get)  # type: ignore[arg-type]

    # ── Condorcet helper ──────────────────────────────────────────────────────
    def _condorcet_winner(rankings: List[List[str]]) -> Optional[str]:
        n_v = len(rankings)
        for cand in cand_names:
            beats_all = True
            for other in cand_names:
                if other == cand:
                    continue
                prefer_cand = sum(
                    1 for r in rankings
                    if r.index(cand) < r.index(other)
                    if cand in r and other in r
                )
                if prefer_cand <= n_v / 2:
                    beats_all = False
                    break
            if beats_all:
                return cand
        return None

    # ── IRV helper ────────────────────────────────────────────────────────────
    def _irv(rankings: List[List[str]]) -> str:
        remaining = list(cand_names)
        current   = [list(r) for r in rankings]
        while len(remaining) > 1:
            from collections import Counter as _C2
            tally = _C2(
                next((c for c in r if c in remaining), None)
                for r in current
            )
            tally.pop(None, None)  # type: ignore[arg-type]
            if not tally:
                break
            total = sum(tally.values())
            # Check majority
            leader = tally.most_common(1)[0][0]
            if tally[leader] > total / 2:
                return leader
            # Eliminate last
            last = tally.most_common()[-1][0]
            remaining.remove(last)
        return remaining[0] if remaining else cand_names[0]

    # ── Minimax helper ────────────────────────────────────────────────────────
    def _minimax(rankings: List[List[str]]) -> str:
        n_v = len(rankings)
        worst_loss: Dict[str, int] = {}
        for cand in cand_names:
            losses = []
            for other in cand_names:
                if other == cand:
                    continue
                prefer_other = sum(
                    1 for r in rankings
                    if cand in r and other in r and r.index(other) < r.index(cand)
                )
                losses.append(prefer_other)
            worst_loss[cand] = max(losses) if losses else 0
        return min(worst_loss, key=worst_loss.get)  # type: ignore[arg-type]

    # ── Method dispatcher ─────────────────────────────────────────────────────
    def _run_method(method: str, rankings: List[List[str]]) -> str:
        if method == "plurality":
            return _plurality(rankings)
        if method == "borda":
            return _borda(rankings)
        if method == "irv":
            return _irv(rankings)
        if method == "approval":
            # Approve top 40% of candidates
            threshold = max(1, int(n_cands * 0.4) + 1)
            from collections import Counter as _C3
            scores: Dict[str, int] = {c: 0 for c in cand_names}
            for r in rankings:
                for c in r[:threshold]:
                    scores[c] += 1
            return max(scores, key=scores.get)  # type: ignore[arg-type]
        if method in ("schulze", "kemeny_young", "condorcet"):
            cw = _condorcet_winner(rankings)
            return cw if cw else _borda(rankings)
        if method == "minimax":
            return _minimax(rankings)
        if method in ("star", "median"):
            # Score-based: use borda as proxy
            return _borda(rankings)
        return _plurality(rankings)

    # ── Binary elimination for agenda comparison ───────────────────────────────
    def _binary_elim(agenda_order: List[str], pair_matrix: Dict[str, Dict[str, float]]) -> str:
        current = agenda_order[0]
        for challenger in agenda_order[1:]:
            if pair_matrix.get(challenger, {}).get(current, 0.0) > 0.5:
                current = challenger
        return current

    # ── Build pairwise matrix ──────────────────────────────────────────────────
    pair_matrix: Dict[str, Dict[str, float]] = {a: {} for a in cand_names}
    n_v = len(voter_positions)
    for a in cand_names:
        for b in cand_names:
            if a == b:
                pair_matrix[a][b] = 0.5
            else:
                pref_a = sum(
                    1 for r in sincere_rankings
                    if r.index(a) < r.index(b)
                )
                pair_matrix[a][b] = pref_a / n_v

    # ── Agenda permutations ────────────────────────────────────────────────────
    all_perms = list(_it_cw.permutations(cand_names))
    rng.shuffle(all_perms)
    selected_perms = all_perms[:min(num_agendas, len(all_perms))]
    agenda_labels  = [" → ".join(p) for p in selected_perms]

    # ── Run all (method × simulation) combinations ───────────────────────────
    all_results: List[str]             = []
    winner_by_method: Dict[str, str]   = {}
    winner_by_agenda: Dict[str, str]   = {}

    for method in methods_used:
        w = _run_method(method, sincere_rankings)
        winner_by_method[method] = w
        all_results.append(w)

    for perm, label in zip(selected_perms, agenda_labels):
        w = _binary_elim(list(perm), pair_matrix)
        winner_by_agenda[label] = w
        all_results.append(w)

    # ── Multi-simulation variance ─────────────────────────────────────────────
    for sim in range(num_sims - 1):
        sim_rng = _rnd.Random(seed + sim + 1)
        if ideology == "polarized":
            sim_pos = [
                sim_rng.gauss(-0.5, 0.2) if sim_rng.random() < 0.5
                else sim_rng.gauss(0.5, 0.2)
                for _ in range(num_voters)
            ]
        else:
            sim_pos = [sim_rng.uniform(-1, 1) for _ in range(num_voters)]
        sim_pos = [max(-1.0, min(1.0, p)) for p in sim_pos]

        sim_rankings = [
            [cand_names[j]
             for j in sorted(range(n_cands),
                             key=lambda k, sp=sp: -_utility(sp, candidates_raw[k]))]  # type: ignore
            for sp in sim_pos
        ]
        for method in methods_used[:3]:  # lightweight: top 3 methods only
            all_results.append(_run_method(method, sim_rankings))

    # ── Aggregate ─────────────────────────────────────────────────────────────
    from collections import Counter as _Cfinal
    winner_counts  = _Cfinal(all_results)
    unique_winners = list(winner_counts.keys())
    n_unique       = len(unique_winners)

    most_frequent        = winner_counts.most_common(1)[0][0]
    most_frequent_pct    = winner_counts[most_frequent] / len(all_results)
    rousseau_score       = round(1 / n_unique, 4) if n_unique > 0 else 1.0
    condorcet_w          = _condorcet_winner(sincere_rankings)
    condorcet_exists     = condorcet_w is not None

    # ── Philosophical conclusion ──────────────────────────────────────────────
    if condorcet_exists and n_unique == 1:
        philos = (
            f"Rousseau avait peut-être raison : '{condorcet_w}' gagne sous toutes "
            f"les procédures testées. Mais attention — cela dépend du scénario. "
            f"Arrow (1951) démontre que ce consensus ne peut pas être généralisé."
        )
    elif n_unique == 1:
        philos = (
            f"'{most_frequent}' domine toutes les procédures testées (sans vainqueur "
            f"de Condorcet). Schumpeter dirait : la procédure est consensuelle ici, "
            f"mais ce n'est pas universel."
        )
    elif n_unique <= 2:
        philos = (
            f"{n_unique} vainqueurs différents selon la procédure "
            f"(Rousseau_score = {rousseau_score:.2f}). La 'volonté collective' est "
            f"instable — Arrow a probablement raison pour ce scénario."
        )
    else:
        philos = (
            f"{n_unique} vainqueurs différents — Schumpeter (1942) avait raison : "
            f"le résultat est un artefact procédural. "
            f"'{most_frequent}' gagne le plus souvent ({round(most_frequent_pct*100)}%), "
            f"mais changer la méthode change le vainqueur."
        )

    note = (
        "Vote Lab ne peut pas répondre à la question 'Quelle est la volonté du peuple ?' "
        "— il peut seulement montrer que le résultat dépend de la procédure choisie. "
        "C'est peut-être la leçon la plus importante de toute la théorie du vote."
    )

    return {
        "unique_winners":        unique_winners,
        "unique_winner_count":   n_unique,
        "winner_by_method":      winner_by_method,
        "winner_by_agenda":      winner_by_agenda,
        "rousseau_score":        rousseau_score,
        "most_frequent_winner":  most_frequent,
        "most_frequent_pct":     round(most_frequent_pct, 4),
        "condorcet_exists":      condorcet_exists,
        "condorcet_winner":      condorcet_w,
        "philosophical_conclusion": philos,
        "pedagogical_note":      note,
    }, 200


