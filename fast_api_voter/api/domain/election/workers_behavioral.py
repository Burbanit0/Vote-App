"""
api.domain.election.workers_behavioral — behavioural / research-panel workers,
split out of the workers.py monolith (incremental decomposition).

Pure `data: dict -> (body, http_status)` workers: information cascade,
behavioural biases, liquid democracy, conviction voting, NOTA, ballot
complexity, shy-voter, electoral fatigue, choice overload. Depends only on the
engine utils + the shared ._electorate / ._helpers.
"""
from __future__ import annotations

import random as _random
from collections import Counter
from typing import Any, Dict, List, Optional  # noqa: F401

import numpy as _np

from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.simulation_voting_utils import calculate_utility, create_voter
from api.engine.utils.simulation_ranked_utils import (
    get_plurality_winner, get_condorcet_winner,
)
from ._electorate import _build_base_electorate
from ._helpers import build_candidate_from_xy as _build_candidate_from_xy


# ── Information Cascade ───────────────────────────────────────────────────────

def _cascade_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /cascade — extracted for FastAPI v2 reuse."""
    num_voters         = max(20,  min(500,  int(data.get("num_voters",         100))))
    ideology           = str(data.get("ideology",          "random"))
    seed               = int(data.get("seed",               42))
    cascade_strength   = max(0.0, min(1.0, float(data.get("cascade_strength",  0.5))))
    observation_window = max(0,   min(50,  int(data.get("observation_window",  10))))
    cand_specs         = data.get("candidates", [
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

    def _sincere_choice(voter_id: Any) -> str:
        return max(sincere_utilities[voter_id], key=lambda k: sincere_utilities[voter_id][k])

    def _run_cascade(
        strength: float, rng: _random.Random
    ) -> tuple[list[Dict[str, Any]], str, Optional[int], float]:
        """Run one cascade pass. Returns (sequence, winner, cascade_start_at, cascade_rate)."""
        votes: list[str] = []
        sequence: list[Dict[str, Any]] = []
        cascade_start: Optional[int] = None
        cascade_count = 0

        for v in voters:
            vid     = v["id"]
            sincere = _sincere_choice(vid)
            followed = False

            if observation_window > 0 and votes and strength > 0:
                window      = votes[-observation_window:]
                pub_signal  = Counter(window).most_common(1)[0][0]
                if rng.random() < strength and pub_signal != sincere:
                    actual_vote = pub_signal
                    followed    = True
                else:
                    actual_vote = sincere
            else:
                actual_vote = sincere

            if followed:
                cascade_count += 1
                if cascade_start is None:
                    cascade_start = vid

            votes.append(actual_vote)
            sequence.append({
                "voter_id":        vid,
                "sincere_choice":  sincere,
                "actual_vote":     actual_vote,
                "followed_cascade": followed,
            })

        winner: str = Counter(votes).most_common(1)[0][0] if votes else cand_names[0]
        rate: float = round(cascade_count / len(voters), 4) if voters else 0.0
        return sequence, winner, cascade_start, rate

    # ── Main run ───────────────────────────────────────────────────────────
    rng  = _random.Random(seed)
    vote_sequence, cascade_winner, cascade_start_at, _ = _run_cascade(cascade_strength, rng)

    # Sincere winner (strength = 0, no randomness needed)
    sincere_votes   = [_sincere_choice(v["id"]) for v in voters]
    sincere_winner: str = Counter(sincere_votes).most_common(1)[0][0]

    cascade_occurred = (cascade_winner != sincere_winner)

    # ── Strength curve (11 steps 0 → 1) ───────────────────────────────────
    cascade_strength_curve: list[Dict[str, Any]] = []
    for step in range(11):
        s        = round(step / 10, 1)
        step_rng = _random.Random(seed)
        _, w, _, cr = _run_cascade(s, step_rng)
        cascade_strength_curve.append({
            "strength":     s,
            "winner":       w,
            "cascade_rate": cr,
        })

    # ── Comparison runs (strength 0, 0.5, 1.0) ────────────────────────────
    comparison_runs = [c for c in cascade_strength_curve if c["strength"] in (0.0, 0.5, 1.0)]

    # Trim sequence for large electorates (keep first 300 for timeline)
    visible_sequence = vote_sequence[:300]

    return {
        "sincere_winner":         sincere_winner,
        "cascade_winner":         cascade_winner,
        "cascade_occurred":       cascade_occurred,
        "vote_sequence":          visible_sequence,
        "cascade_start_at":       cascade_start_at,
        "cascade_strength_curve": cascade_strength_curve,
        "comparison_runs":        comparison_runs,
        "candidates":             cand_names,
    }, 200


# ── Behavioral Biases ─────────────────────────────────────────────────────────

def _behavioral_biases_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /behavioral-biases — extracted for FastAPI v2 reuse.

    Model three empirical voting biases and their impact on election outcomes:
      1. Expressive voting (Fiorina 1976): voters boost their ideal candidate ×10,
         inflating the approval threshold so they behave like bullet voters.
      2. Bullet voting: approval voters approve only their top choice, collapsing
         Approval Voting to Plurality for those voters.
      3. Primacy effect (Krosnick 1991): the first-listed candidate gains a vote
         bonus proportional to primacy_bonus.
    """
    import copy as _copy

    num_voters        = max(50,  min(500,  int(data.get("num_voters",         200))))
    ideology          = str(data.get("ideology",           "random"))
    seed              = int(data.get("seed",                42))
    expressive_pct    = max(0.0, min(1.0, float(data.get("expressive_pct",    0.2))))
    bullet_pct        = max(0.0, min(1.0, float(data.get("bullet_voting_pct", 0.2))))
    primacy_bonus     = max(0.0, min(0.2, float(data.get("primacy_bonus",     0.02))))
    # Pydantic Optional[List[str]] may pass null — fall back to [].
    candidate_order   = [str(n) for n in (data.get("candidate_order") or [])]
    primary_method    = str(data.get("method", "plurality"))
    cand_specs        = data.get("candidates", [
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

    # ── Resolve candidate order for primacy ───────────────────────────────
    name_set = set(cand_names)
    ordered_names: list[str] = [n for n in candidate_order if n in name_set]
    if len(ordered_names) != len(cand_names):
        ordered_names = list(cand_names)
    first_listed = ordered_names[0]

    # ── Select affected voter subsets ─────────────────────────────────────
    all_ids       = [v["id"] for v in voters]
    rng           = _random.Random(seed)
    exp_count     = round(expressive_pct * num_voters)
    bullet_count  = round(bullet_pct     * num_voters)
    primacy_count = round(primacy_bonus  * num_voters)

    expressive_ids = set(rng.sample(all_ids, min(exp_count,     len(all_ids))))
    bullet_ids     = set(rng.sample(all_ids, min(bullet_count,  len(all_ids))))
    primacy_ids    = set(rng.sample(all_ids, min(primacy_count, len(all_ids))))

    # ── Build biased utilities ────────────────────────────────────────────
    biased_utilities: Dict[Any, Dict[str, float]] = _copy.deepcopy(sincere_utilities)

    for v in voters:
        vid = v["id"]
        u   = biased_utilities[vid]
        # Expressive: emotional attachment inflates ideal candidate utility ×10
        if vid in expressive_ids:
            ideal = max(u, key=lambda k: u[k])
            u[ideal] = u[ideal] * 10.0
        # Primacy: position bias nudges voter toward first-listed candidate
        if vid in primacy_ids:
            curr_max        = max(u.values())
            u[first_listed] = curr_max + 0.1

    # ── Fast winner computation (no strategic-vulnerability overhead) ──────
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner as _borda,
        get_irv_winner   as _irv,
        get_schulze_winner as _schulze,
    )
    from api.engine.utils.simulation_score_utils import (
        get_star_voting_winner        as _star,
        get_majority_judgment_winner  as _mj,
    )

    def _compute_winners(utils: Dict[Any, Dict[str, float]]) -> Dict[str, Optional[str]]:
        rnk = [
            sorted(utils[v["id"]].keys(), key=lambda n: -utils[v["id"]][n])
            for v in voters
        ]
        sv = [
            {n: max(0, min(5, round(5 * val))) for n, val in utils[v["id"]].items()}
            for v in voters
        ]
        out: Dict[str, Optional[str]] = {}
        for mname, fn in [("plurality", get_plurality_winner),
                           ("borda",    _borda),
                           ("irv",      _irv),
                           ("schulze",  _schulze)]:
            try:
                out[mname] = fn(rnk)
            except Exception:
                out[mname] = None
        try:
            raw = _star(sv)
            out["star_voting"] = raw.get("winner") if isinstance(raw, dict) else raw
        except Exception:
            out["star_voting"] = None
        try:
            mj_utils = [dict(utils[v["id"]]) for v in voters]
            mj_raw   = _mj(mj_utils)
            out["majority_judgment"] = str(mj_raw["winner"]) if mj_raw.get("winner") else None
        except Exception:
            out["majority_judgment"] = None
        return out

    # ── Approval with bullet voting ───────────────────────────────────────
    def _approval_winner(utils: Dict[Any, Dict[str, float]], bids: set[Any]) -> str:
        tally: Counter[Any] = Counter()
        for v in voters:
            vid = v["id"]
            u   = utils[vid]
            if not u:
                continue
            if vid in bids:
                tally[max(u, key=lambda k: u[k])] += 1
            else:
                threshold = sum(u.values()) / len(u)
                for cname, val in u.items():
                    if val > threshold:
                        tally[cname] += 1
        return max(tally, key=tally.__getitem__) if tally else cand_names[0]

    sincere_winners  = _compute_winners(sincere_utilities)
    biased_winners   = _compute_winners(biased_utilities)

    # Approval computed separately for both runs
    sincere_winners["approval"] = _approval_winner(sincere_utilities, set())
    biased_winners["approval"]  = _approval_winner(biased_utilities,  bullet_ids)

    # ── Method sensitivity table ──────────────────────────────────────────
    TRACKED = ["plurality", "approval", "borda", "irv",
               "schulze", "star_voting", "majority_judgment"]
    method_sensitivity: Dict[str, Dict[str, Optional[str]]] = {
        m: {"sincere": sincere_winners.get(m), "biased": biased_winners.get(m)}
        for m in TRACKED
        if sincere_winners.get(m) or biased_winners.get(m)
    }

    # ── Headline comparison ───────────────────────────────────────────────
    sincere_winner = sincere_winners.get(primary_method) or cand_names[0]
    biased_winner  = biased_winners.get(primary_method)  or cand_names[0]
    winner_changed = sincere_winner != biased_winner

    # ── Pedagogical note ──────────────────────────────────────────────────
    changed_methods = [m for m, d in method_sensitivity.items()
                       if d["sincere"] != d["biased"]]
    if winner_changed:
        note = (
            f"Ces biais comportementaux changent le vainqueur de {sincere_winner}"
            f" à {biased_winner} sous la méthode '{primary_method}'. "
            f"{len(changed_methods)} méthode(s) affectée(s) : "
            f"{', '.join(changed_methods[:4])}."
        )
    else:
        if changed_methods:
            note = (
                f"Le vainqueur sincère ({sincere_winner}) est maintenu sous '{primary_method}', "
                f"mais {len(changed_methods)} autre(s) méthode(s) changent de vainqueur "
                f"sous ces biais : {', '.join(changed_methods[:4])}."
            )
        else:
            note = (
                "Aucune méthode ne change de vainqueur malgré ces biais comportementaux. "
                "L'électorat est suffisamment homogène pour résister aux distorsions."
            )

    return {
        "sincere_winner":   sincere_winner,
        "biased_winner":    biased_winner,
        "winner_changed":   winner_changed,
        "vote_breakdown": {
            "expressive_voters": exp_count,
            "bullet_voters":     bullet_count,
            "primacy_affected":  primacy_count,
            "first_listed":      first_listed,
            "candidate_order":   ordered_names,
        },
        "method_sensitivity":    method_sensitivity,
        "bullet_immune_methods": ["majority_judgment", "star_voting",
                                  "borda", "irv", "schulze"],
        "pedagogical_note":      note,
    }, 200


# ── Liquid Democracy ──────────────────────────────────────────────────────────

_LD_DEFAULT_CANDIDATES = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.1},
]

_Delegations = Dict[int, int]


def _ld_voter_positions(voters: List[Dict[str, Any]]) -> Dict[int, tuple[float, float]]:
    """Each voter on the same [-1, 1] plane as the candidates, for the
    nearest-delegate lookup."""
    return {
        v["id"]: (
            round(2.0 * v["issue_positions"].get("economy",        0.5) - 1.0, 3),
            round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
        )
        for v in voters
    }


def _ld_pick_delegate(
    voter_id: int,
    all_ids: List[int],
    strategy: str,
    voter_positions: Dict[int, tuple[float, float]],
    sincere_utilities: Dict[int, Dict[str, float]],
    rng: _random.Random,
) -> int:
    """Who this voter hands their vote to, under the chosen strategy."""
    others = [v for v in all_ids if v != voter_id]
    if not others:
        return voter_id
    if strategy == "nearest":
        vx, vy = voter_positions[voter_id]
        return min(others, key=lambda o: (voter_positions[o][0] - vx) ** 2
                                       + (voter_positions[o][1] - vy) ** 2)
    if strategy == "most_competent":
        return max(others, key=lambda o: max(sincere_utilities[o].values()))
    return rng.choice(others)  # "random"


def _ld_detect_cycles(delg: _Delegations) -> set[int]:
    """Nodes sitting on a delegation cycle. The graph is functional — every node
    has at most one outgoing edge — so walking forward from each unvisited node
    either leaves the graph or re-enters the path, and re-entry is the cycle."""
    in_cycle: set[int] = set()
    visited:  set[int] = set()
    for start in list(delg.keys()):
        if start in visited:
            continue
        path: list[int] = []
        path_pos: Dict[int, int] = {}
        cur = start
        while cur not in visited and cur not in path_pos and cur in delg:
            path_pos[cur] = len(path)
            path.append(cur)
            cur = delg[cur]
        if cur in path_pos:
            for node in path[path_pos[cur]:]:
                in_cycle.add(node)
        visited.update(path)
    return in_cycle


def _ld_resolve(
    all_ids: List[int],
    delg: _Delegations,
    in_cycle: set[int],
    max_chain: int,
) -> tuple[_Delegations, Dict[int, int]]:
    """Follow each delegation chain to the voter who actually casts the ballot.
    A voter on a cycle, or one whose chain runs past `max_chain`, votes for
    themselves. Returns the effective voter per id, and the chain length for
    those that resolved."""
    effective: _Delegations = {}
    chain_lengths: Dict[int, int] = {}
    for vid in all_ids:
        if vid not in delg or vid in in_cycle:
            effective[vid] = vid
            continue
        cur, steps = vid, 0
        while cur in delg and cur not in in_cycle and steps < max_chain:
            cur = delg[cur]
            steps += 1
        if cur not in delg or cur in in_cycle:
            effective[vid] = cur
            chain_lengths[vid] = steps
        else:
            effective[vid] = vid   # max chain exhausted → vote directly
    return effective, chain_lengths


def _ld_gini(vals: List[Any]) -> float:
    """Gini coefficient of the voting-weight distribution: 0 when every voter
    carries the same weight, approaching 1 as it concentrates on a few."""
    n = len(vals)
    if n == 0:
        return 0.0
    s = sorted(float(v) for v in vals)
    total = sum(s)
    if total == 0.0:
        return 0.0
    cumsum = sum((i + 1) * v for i, v in enumerate(s))
    return round(abs(2.0 * cumsum / (n * total) - (n + 1) / n), 4)


def _ld_top_choice(sincere_utilities: Dict[int, Dict[str, float]], vid: int) -> str:
    """The candidate this voter most prefers."""
    return max(sincere_utilities[vid], key=lambda k: sincere_utilities[vid][k])


def _ld_tally(
    weighted_ids: List[tuple[int, int]],
    sincere_utilities: Dict[int, Dict[str, float]],
    fallback: str,
) -> tuple[Counter[Any], str]:
    """Plurality over each voter's top choice, each carrying their own weight.
    The liquid tally weights by delegations received; the direct baseline gives
    everyone 1."""
    tally: Counter[Any] = Counter()
    for vid, w in weighted_ids:
        tally[_ld_top_choice(sincere_utilities, vid)] += w
    return tally, (max(tally, key=tally.__getitem__) if tally else fallback)


def _ld_gini_curve(
    all_ids: List[int],
    pick: Any,
    sincere_utilities: Dict[int, Dict[str, float]],
    max_chain: int,
    seed: int,
) -> List[Dict[str, Any]]:
    """How weight concentration grows with the delegation rate, in 11 steps from
    0 to 1. Each step redraws who delegates from a fresh stream, but keeps
    drawing *whom* they delegate to from the caller's shared rng — so a run of
    the curve advances that stream exactly as it did before this was extracted."""
    curve: List[Dict[str, Any]] = []
    for step in range(11):
        p = round(step / 10, 1)
        g_rng = _random.Random(seed)
        g_delg: _Delegations = {
            vid: pick(vid) for vid in all_ids if g_rng.random() < p
        }
        g_eff, _ = _ld_resolve(all_ids, g_delg, _ld_detect_cycles(g_delg), max_chain)
        g_w = Counter(g_eff.values())
        curve.append({
            "probability": p,
            "gini": _ld_gini([g_w.get(v, 0) for v in all_ids]),
        })
    return curve


def _ld_note(
    delegation_prob: float,
    strategy: str,
    top3_pct: int,
    gini: float,
    liquid_winner: str,
    direct_winner: str,
) -> str:
    header = f"Avec {round(delegation_prob * 100)}% de délégation ({strategy}), "
    if liquid_winner != direct_winner:
        return header + (
            f"3 super-votants concentrent {top3_pct}% du poids électoral (Gini={gini}). "
            f"La Liquid Democracy change le vainqueur : {direct_winner} → {liquid_winner}."
        )
    return header + (
        f"{top3_pct}% du poids va aux 3 premiers super-votants (Gini={gini}). "
        f"Le vainqueur reste {liquid_winner} malgré la concentration."
    )


def _liquid_democracy_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /liquid-democracy — extracted for FastAPI v2."""
    num_voters      = max(2, min(500, int(data.get("num_voters", 100))))
    ideology        = str(data.get("ideology", "random"))
    seed            = int(data.get("seed", 42))
    delegation_prob = max(0.0, min(1.0, float(data.get("delegation_probability", 0.5))))
    strategy        = str(data.get("delegation_strategy", "nearest"))
    max_chain       = max(1, min(20, int(data.get("max_chain_length", 5))))
    cand_specs      = data.get("candidates", _LD_DEFAULT_CANDIDATES)[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    all_ids: list[int] = [v["id"] for v in voters]
    voter_positions = _ld_voter_positions(voters)
    rng = _random.Random(seed)

    def pick(vid: int) -> int:
        return _ld_pick_delegate(
            vid, all_ids, strategy, voter_positions, sincere_utilities, rng,
        )

    delegations: _Delegations = {
        vid: pick(vid) for vid in all_ids if rng.random() < delegation_prob
    }
    in_cycle = _ld_detect_cycles(delegations)
    effective, chain_lengths = _ld_resolve(all_ids, delegations, in_cycle, max_chain)
    weights: Counter[Any] = Counter(effective.values())

    liquid_tally, liquid_winner = _ld_tally(
        list(weights.items()), sincere_utilities, cand_names[0],
    )
    _, direct_winner = _ld_tally(
        [(v["id"], 1) for v in voters], sincere_utilities, cand_names[0],
    )

    gini    = _ld_gini([weights.get(vid, 0) for vid in all_ids])
    lengths = list(chain_lengths.values())
    by_weight = sorted(weights.items(), key=lambda x: -x[1])

    super_voters = [
        {
            "id":     vid,
            "weight": w,
            "x":      voter_positions[vid][0],
            "y":      voter_positions[vid][1],
            "choice": _ld_top_choice(sincere_utilities, vid),
        }
        for vid, w in by_weight[:10]
        if w >= 2
    ]

    total_w  = sum(weights.values())
    top3_pct = round(100 * sum(w for _, w in by_weight[:3]) / total_w) if total_w else 0

    return {
        "weighted_results":   {c: int(liquid_tally.get(c, 0)) for c in cand_names},
        "direct_voters":      sum(1 for vid in all_ids if effective[vid] == vid),
        "delegators":         sum(1 for vid in all_ids if effective[vid] != vid),
        "super_voters":       super_voters,
        "delegation_graph":   [
            {"from": d, "to": t} for d, t in delegations.items()
        ][:500],
        "cycles_detected":    len(in_cycle),
        "cycle_voter_ids":    list(in_cycle),
        "chain_stats": {
            "mean": round(sum(lengths) / len(lengths), 2) if lengths else 0.0,
            "max":  max(lengths) if lengths else 0,
        },
        "gini_curve":         _ld_gini_curve(
            all_ids, pick, sincere_utilities, max_chain, seed,
        ),
        "comparison": {
            "liquid_winner":  liquid_winner,
            "direct_winner":  direct_winner,
            "winner_changed": liquid_winner != direct_winner,
        },
        "gini_voting_weight": gini,
        "pedagogical_note":   _ld_note(
            delegation_prob, strategy, top3_pct, gini, liquid_winner, direct_winner,
        ),
    }, 200


# ── Conviction Voting ─────────────────────────────────────────────────────────

_CV_LOCK_OPTIONS: list[int]    = [0, 7, 14, 28, 56, 112, 224]
_CV_MULTIPLIERS:  Dict[int, float] = {0: 0.1, 7: 1.0, 14: 2.0, 28: 3.0,
                                       56: 4.0, 112: 5.0, 224: 6.0}


def _conviction_voting_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /conviction-voting — extracted for FastAPI v2."""
    num_voters     = max(20, min(500, int(data.get("num_voters",   200))))
    ideology       = str(data.get("ideology",       "random"))
    seed           = int(data.get("seed",            42))
    cv_dist        = str(data.get("conviction_distribution", "uniform"))
    whale_pct      = max(0.05, min(0.5, float(data.get("whale_pct",       0.10))))
    small_lock_d   = int(data.get("small_lock_days", 224))
    small_lock_d   = small_lock_d if small_lock_d in _CV_LOCK_OPTIONS else 224
    proposals_in   = data.get("proposals", [
        {"name": "Proposition A", "x": -0.5},
        {"name": "Proposition B", "x":  0.5},
        {"name": "Proposition C", "x":  0.0},
    ])[:8]

    if len(proposals_in) < 2:
        return {"error": "At least 2 proposals required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    # ── Electorate ────────────────────────────────────────────────────────
    voters = [
        create_voter(issues, i, ideology_distribution=ideology)
        for i in range(num_voters)
    ]
    all_ids: list[int] = [v["id"] for v in voters]

    # ── Token distribution (Pareto a=1.16 — realistic crypto inequality) ──
    raw_tokens = _np.random.pareto(1.16, num_voters) + 1.0
    tokens_arr = raw_tokens / raw_tokens.mean() * 1000.0          # mean ≈ 1000
    voter_tokens: Dict[int, float] = {
        v["id"]: float(tokens_arr[i]) for i, v in enumerate(voters)
    }

    # ── Token rank (0 = smallest holder) ──────────────────────────────────
    tok_vals     = _np.array([voter_tokens[vid] for vid in all_ids])
    rank_arr     = _np.argsort(_np.argsort(tok_vals)) / max(1, len(all_ids) - 1)
    token_ranks: Dict[int, float] = {all_ids[i]: float(rank_arr[i]) for i in range(len(all_ids))}

    rng = _random.Random(seed + 1)

    # ── Assign conviction lock ────────────────────────────────────────────
    def _assign_lock(voter_id: int) -> int:
        rank = token_ranks[voter_id]
        if cv_dist == "uniform":
            return rng.choice(_CV_LOCK_OPTIONS)
        if cv_dist == "skewed":
            # Smaller holders lock longer (inverse relationship with token rank)
            lock_idx = min(6, round((1.0 - rank) * 6.0))
            return _CV_LOCK_OPTIONS[lock_idx]
        if cv_dist == "whale":
            # Top whale_pct% by tokens → no lock; rest → small_lock_d
            return 0 if rank >= (1.0 - whale_pct) else small_lock_d
        if cv_dist == "zero_lock":
            return 0
        return rng.choice(_CV_LOCK_OPTIONS)

    voter_lock:    Dict[int, int]   = {vid: _assign_lock(vid) for vid in all_ids}
    voter_mult:    Dict[int, float] = {vid: _CV_MULTIPLIERS[voter_lock[vid]] for vid in all_ids}
    voter_cv_w:    Dict[int, float] = {vid: voter_tokens[vid] * voter_mult[vid] for vid in all_ids}

    # ── Voter ideology → proposal choice ─────────────────────────────────
    prop_names: list[str]   = [p["name"] for p in proposals_in]
    prop_x:     Dict[str, float] = {p["name"]: float(p.get("x", 0.0)) for p in proposals_in}

    voter_ide: Dict[int, float] = {
        v["id"]: 2.0 * v["issue_positions"].get("economy", 0.5) - 1.0
        for v in voters
    }
    voter_choice: Dict[int, str] = {
        vid: min(prop_names, key=lambda pn: abs(voter_ide[vid] - prop_x[pn]))
        for vid in all_ids
    }

    # ── Tally ─────────────────────────────────────────────────────────────
    cv_tally:  Dict[str, float] = {p: 0.0 for p in prop_names}
    tok_tally: Dict[str, float] = {p: 0.0 for p in prop_names}

    for vid in all_ids:
        ch = voter_choice[vid]
        cv_tally[ch]  += voter_cv_w[vid]
        tok_tally[ch] += voter_tokens[vid]

    conviction_winner: str = max(cv_tally,  key=cv_tally.__getitem__)
    token_winner:      str = max(tok_tally, key=tok_tally.__getitem__)
    winner_changed         = conviction_winner != token_winner

    # ── Per-proposal stats ────────────────────────────────────────────────
    proposal_stats: list[Dict[str, Any]] = []
    for p in proposals_in:
        pn   = p["name"]
        supp = [vid for vid in all_ids if voter_choice[vid] == pn]
        proposal_stats.append({
            "name":                        pn,
            "conviction_score":            round(cv_tally[pn],  2),
            "token_score":                 round(tok_tally[pn], 2),
            "avg_conviction_of_supporters": round(
                sum(voter_mult[vid] for vid in supp) / len(supp), 3
            ) if supp else 0.0,
            "avg_tokens_of_supporters": round(
                sum(voter_tokens[vid] for vid in supp) / len(supp), 2
            ) if supp else 0.0,
        })

    # ── Gini + whale stats ────────────────────────────────────────────────
    def _gini(vals: List[Any]) -> float:
        n = len(vals)
        if n == 0:
            return 0.0
        s     = sorted(float(v) for v in vals)
        total = sum(s)
        if total == 0.0:
            return 0.0
        cumsum = sum((i + 1) * v for i, v in enumerate(s))
        return round(abs(2.0 * cumsum / (n * total) - (n + 1) / n), 4)

    all_tok = [voter_tokens[vid] for vid in all_ids]
    all_cvw = [voter_cv_w[vid]   for vid in all_ids]

    top_n          = max(1, round(whale_pct * num_voters))
    top_tok        = sorted(all_tok, reverse=True)[:top_n]
    top_cvw        = sorted(all_cvw, reverse=True)[:top_n]
    sum_tok        = sum(all_tok) or 1.0
    sum_cvw        = sum(all_cvw) or 1.0

    voter_stats: Dict[str, float] = {
        "gini_tokens":          _gini(all_tok),
        "gini_conviction":      _gini(all_cvw),
        "whale_pct_tokens":     round(sum(top_tok) / sum_tok, 4),
        "whale_pct_conviction": round(sum(top_cvw) / sum_cvw, 4),
    }

    # ── Voter scatter sample (max 300) ────────────────────────────────────
    voter_scatter: list[Dict[str, Any]] = [
        {
            "id":               vid,
            "tokens":           round(voter_tokens[vid], 1),
            "lock_days":        voter_lock[vid],
            "conviction_mult":  voter_mult[vid],
            "conviction_weight": round(voter_cv_w[vid], 1),
            "choice":           voter_choice[vid],
        }
        for vid in all_ids[:300]
    ]

    # ── Pedagogical note ──────────────────────────────────────────────────
    max_cv_vid  = max(all_ids, key=lambda v: voter_cv_w[v])
    max_tok_vid = max(all_ids, key=lambda v: voter_tokens[v])
    note = (
        f"Un votant avec {round(voter_tokens[max_cv_vid])} tokens "
        f"et {voter_lock[max_cv_vid]} jours de lock pèse "
        f"{round(voter_cv_w[max_cv_vid])} points de conviction. "
        f"La baleine principale ({round(voter_tokens[max_tok_vid])} tokens, "
        f"{voter_lock[max_tok_vid]} jours) pèse "
        f"{round(voter_cv_w[max_tok_vid])} points. "
    )
    if voter_stats["gini_conviction"] < voter_stats["gini_tokens"]:
        note += (
            f"La conviction réduit l'inégalité effective "
            f"(Gini tokens={voter_stats['gini_tokens']} → "
            f"conviction={voter_stats['gini_conviction']})."
        )
    else:
        note += (
            f"Dans ce scénario, la conviction n'atténue pas l'inégalité "
            f"(Gini tokens={voter_stats['gini_tokens']}, "
            f"conviction={voter_stats['gini_conviction']})."
        )

    return {
        "conviction_winner": conviction_winner,
        "token_winner":      token_winner,
        "winner_changed":    winner_changed,
        "proposals":         proposal_stats,
        "voter_scatter":     voter_scatter,
        "voter_stats":       voter_stats,
        "pedagogical_note":  note,
        "lock_options":      _CV_LOCK_OPTIONS,
        "multipliers":       {str(k): v for k, v in _CV_MULTIPLIERS.items()},
    }, 200


# ── NOTA (None Of The Above) ──────────────────────────────────────────────────

# How inclusive each method is: lower adjustment → fewer NOTA voters
# (method integrates more preference information → voter finds more to approve)
_NOTA_ADJ: Dict[str, float] = {
    "plurality":          1.00,
    "two_round":          1.00,
    "borda":              0.95,
    "irv":                0.95,
    "schulze":            0.90,
    "kemeny_young":       0.90,
    "coombs":             0.95,
    "bucklin":            0.95,
    "minimax":            0.90,
    "copeland":           0.92,
    "nanson":             0.92,
    "baldwin":            0.92,
    "approval":           0.50,   # most inclusive: approval of partial satisfaction
    "simple_score":       0.70,
    "star_voting":        0.70,
    "median_voting":      0.80,
    "mean_median_hybrid": 0.80,
    "variance_based":     0.80,
    "majority_judgment":  0.70,
    "quadratic":          0.75,
}

_NOTA_TRACKED = [
    "plurality", "approval", "borda", "irv", "schulze", "majority_judgment",
]


def _nota_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /nota — extracted for FastAPI v2 reuse (Phase 3 batch 3)."""

    num_voters     = max(50,  min(500, int(data.get("num_voters",     200))))
    ideology       = str(data.get("ideology",      "random"))
    seed           = int(data.get("seed",           42))
    nota_threshold = max(0.0, min(1.0, float(data.get("nota_threshold", 0.3))))
    nota_rule      = str(data.get("nota_rule",     "invalidate"))
    primary_method = str(data.get("method",        "plurality"))
    cand_specs     = data.get("candidates", [
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

    # ── NOTA determination for a given method+threshold ───────────────────
    def _nota_pct(threshold: float, method: str = "plurality") -> float:
        adj           = _NOTA_ADJ.get(method, 1.0)
        eff_threshold = threshold * adj
        count = sum(
            1 for v in voters
            if max(sincere_utilities[v["id"]].values()) < eff_threshold
        )
        return round(count / num_voters, 4) if num_voters else 0.0

    # ── Winner with NOTA (plurality model for simplicity) ─────────────────
    def _winner_with_nota(threshold: float) -> tuple[Optional[str], float]:
        """Returns (sincere plurality winner or 'NOTA', nota_pct)."""
        tally: Counter[Any] = Counter()
        for v in voters:
            vid      = v["id"]
            max_util = max(sincere_utilities[vid].values())
            if max_util < threshold:
                tally["NOTA"] += 1
            else:
                choice = max(sincere_utilities[vid], key=lambda k: sincere_utilities[vid][k])
                tally[choice] += 1
        raw_winner = max(tally, key=tally.__getitem__) if tally else cand_names[0]
        np         = tally.get("NOTA", 0) / num_voters if num_voters else 0.0
        return raw_winner, round(np, 4)

    # ── Sincere winners per method (without NOTA) ─────────────────────────
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner as _borda, get_irv_winner as _irv,
        get_schulze_winner as _schulze,
    )
    from api.engine.utils.simulation_score_utils import get_majority_judgment_winner as _mj

    def _sincere_winner(method: str) -> Optional[str]:
        rnk = [
            sorted(sincere_utilities[v["id"]].keys(),
                   key=lambda n: -sincere_utilities[v["id"]][n])
            for v in voters
        ]
        if method in ("plurality", "two_round"):
            return get_plurality_winner(rnk)
        if method == "borda":
            return _borda(rnk)
        if method == "irv":
            return _irv(rnk)
        if method == "schulze":
            return _schulze(rnk)
        if method == "approval":
            # sincere approval: approve above voter mean
            tally: Counter[Any] = Counter()
            for v in voters:
                u  = sincere_utilities[v["id"]]
                th = sum(u.values()) / len(u) if u else 0.5
                for cname, val in u.items():
                    if val > th:
                        tally[cname] += 1
            return max(tally, key=tally.__getitem__) if tally else cand_names[0]
        if method == "majority_judgment":
            mj_utils = [dict(sincere_utilities[v["id"]]) for v in voters]
            try:
                mj_raw = _mj(mj_utils)
                return str(mj_raw["winner"]) if mj_raw.get("winner") else None
            except Exception:
                return None
        return get_plurality_winner(rnk)

    # ── Main computation ──────────────────────────────────────────────────
    nota_pct_main = _nota_pct(nota_threshold, primary_method)
    raw_winner, _ = _winner_with_nota(nota_threshold)
    nota_wins_main = raw_winner == "NOTA"

    def _apply_nota_rule(nota_wins: bool, raw: Optional[str]) -> tuple[Optional[str], bool]:
        if not nota_wins:
            return raw, True
        if nota_rule == "winner_take_all":
            return "NOTA", True
        return None, False   # invalidate / runoff → null winner, invalid election

    final_winner, election_valid = _apply_nota_rule(nota_wins_main, raw_winner)

    # ── Nota curve (20 points: 0.00 → 0.95, step 0.05) ──────────────────
    nota_curve: list[Dict[str, Any]] = []
    sincere_w_primary = _sincere_winner(primary_method)
    for i in range(20):
        t          = round(i * 0.05, 2)
        np_t       = _nota_pct(t, primary_method)
        raw_t, _   = _winner_with_nota(t)
        nota_wins_t = raw_t == "NOTA"
        w_t, _     = _apply_nota_rule(nota_wins_t, sincere_w_primary if not nota_wins_t else None)
        nota_curve.append({
            "threshold": t,
            "nota_pct":  np_t,
            "nota_wins": nota_wins_t,
            "winner":    w_t,
        })

    # ── Method comparison ─────────────────────────────────────────────────
    method_comparison: Dict[str, Any] = {}
    for meth in _NOTA_TRACKED:
        np_m       = _nota_pct(nota_threshold, meth)
        nota_wins_m = np_m > 0.5
        sincere_m  = _sincere_winner(meth)
        w_m, v_m   = _apply_nota_rule(nota_wins_m, sincere_m)
        method_comparison[meth] = {
            "winner":         w_m,
            "nota_pct":       np_m,
            "election_valid": v_m,
        }

    # ── Pedagogical note ──────────────────────────────────────────────────
    most_inclusive = min(
        _NOTA_TRACKED,
        key=lambda m: method_comparison[m]["nota_pct"],
    )
    note = (
        f"Avec un seuil de {nota_threshold}, "
        f"{round(nota_pct_main * 100)}% de l'électorat voterait NOTA "
        f"sous la méthode '{primary_method}'. "
        f"La méthode '{most_inclusive}' génère seulement "
        f"{round(method_comparison[most_inclusive]['nota_pct'] * 100)}% de NOTA "
        f"— elle est plus inclusive car elle intègre davantage de préférences individuelles."
    )

    return {
        "nota_pct":          nota_pct_main,
        "election_valid":    election_valid,
        "winner":            final_winner,
        "nota_curve":        nota_curve,
        "method_comparison": method_comparison,
        "pedagogical_note":  note,
        "nota_rule":         nota_rule,
        "nota_threshold":    nota_threshold,
    }, 200


# ── Ballot Complexity ─────────────────────────────────────────────────────────

# Base error rate per voting method (empirically motivated)
_BALLOT_ERROR_BASE: Dict[str, float] = {
    "plurality":          0.010,
    "two_round":          0.012,
    "approval":           0.025,
    "irv":                0.040,
    "borda":              0.045,
    "star_voting":        0.035,
    "majority_judgment":  0.030,
    "schulze":            0.050,
    "kemeny_young":       0.060,
}

_DEFAULT_BALLOT_METHODS = [
    "plurality", "approval", "irv", "borda",
    "star_voting", "majority_judgment", "schulze",
]


def _ballot_complexity_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /ballot-complexity — extracted for FastAPI v2 reuse."""
    num_voters       = max(50, min(500, int(data.get("num_voters",              200))))
    ideology         = str(data.get("ideology",              "random"))
    seed             = int(data.get("seed",                   42))
    education_level  = max(0.0, min(1.0, float(data.get("education_level",     0.7))))
    ftv_pct          = max(0.0, min(1.0, float(data.get("first_time_voter_pct", 0.1))))
    # Pydantic Optional[List[str]]=None may pass null explicitly — fall back
    # to the server default in that case rather than indexing into None.
    methods_compare  = (data.get("methods_to_compare") or _DEFAULT_BALLOT_METHODS)[:8]
    cand_specs       = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:8]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    n_cands = len(cand_names)

    # ── Null rate formula ─────────────────────────────────────────────────
    def _null_rate(method: str, n: int = n_cands) -> float:
        base = _BALLOT_ERROR_BASE.get(method, 0.03)
        rate = (base
                * (1.0 + 0.08 * max(0, n - 3))
                * (2.0 - education_level)
                * (1.0 + ftv_pct))
        return round(min(1.0, rate), 4)

    # ── Blank rate (intentional blank vote: max utility < 0.3) ───────────
    blank_rate_global = round(
        sum(1 for v in voters if max(sincere_utilities[v["id"]].values()) < 0.3)
        / num_voters, 4,
    )

    # ── Fast winner per method ────────────────────────────────────────────
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner as _borda_w,
        get_irv_winner   as _irv_w,
        get_schulze_winner as _sch_w,
    )
    from api.engine.utils.simulation_score_utils import (
        get_star_voting_winner       as _star_w,
        get_majority_judgment_winner as _mj_w,
    )

    def _winner_for(method: str, vlist: list[Dict[str, Any]]) -> Optional[str]:
        if not vlist:
            return None
        rnk = [
            sorted(sincere_utilities[v["id"]].keys(),
                   key=lambda n: -sincere_utilities[v["id"]][n])
            for v in vlist
        ]
        sv = [
            {n: max(0, min(5, round(5 * sincere_utilities[v["id"]][n])))
             for n in cand_names}
            for v in vlist
        ]
        if method in ("plurality", "two_round"):
            return get_plurality_winner(rnk)
        if method == "borda":
            return _borda_w(rnk)
        if method == "irv":
            return _irv_w(rnk)
        if method == "schulze":
            return _sch_w(rnk)
        if method == "approval":
            tally: Counter[Any] = Counter()
            for v in vlist:
                u  = sincere_utilities[v["id"]]
                th = sum(u.values()) / len(u) if u else 0.5
                for cname, val in u.items():
                    if val > th:
                        tally[cname] += 1
            return max(tally, key=tally.__getitem__) if tally else cand_names[0]
        if method == "star_voting":
            try:
                raw = _star_w(sv)
                return raw.get("winner") if isinstance(raw, dict) else raw
            except Exception:
                return get_plurality_winner(rnk)
        if method == "majority_judgment":
            try:
                mj_u = [dict(sincere_utilities[v["id"]]) for v in vlist]
                raw  = _mj_w(mj_u)
                return str(raw["winner"]) if raw.get("winner") else None
            except Exception:
                return get_plurality_winner(rnk)
        return get_plurality_winner(rnk)

    # ── Per-method simulation ─────────────────────────────────────────────
    results: list[Dict[str, Any]] = []
    sincere_winners: Dict[str, Optional[str]] = {
        m: _winner_for(m, voters) for m in methods_compare
    }

    for i, method in enumerate(methods_compare):
        nr         = _null_rate(method)
        method_rng = _random.Random(seed + 1000 + i)
        valid_voters = [v for v in voters if method_rng.random() >= nr]
        valid_w      = _winner_for(method, valid_voters)
        results.append({
            "method":           method,
            "null_rate":        nr,
            "blank_rate":       blank_rate_global,
            "effective_voters": len(valid_voters),
            "winner":           valid_w,
            "winner_changed":   valid_w != sincere_winners[method],
        })

    # ── Candidate count curve (analytical) ───────────────────────────────
    candidate_count_curve: list[Dict[str, Any]] = [
        {
            "n_candidates": n,
            "null_rate_by_method": {
                m: _null_rate(m, n) for m in methods_compare
            },
        }
        for n in range(2, 11)
    ]

    # ── Most / least inclusive ────────────────────────────────────────────
    nr_map = {r["method"]: r["null_rate"] for r in results}
    most_inclusive  = min(nr_map, key=nr_map.__getitem__)
    least_inclusive = max(nr_map, key=nr_map.__getitem__)

    # ── Pedagogical note ──────────────────────────────────────────────────
    plurality_nr = nr_map.get("plurality", nr_map[methods_compare[0]])
    worst_nr     = nr_map[least_inclusive]
    note = (
        f"Avec {n_cands} candidats, {round(ftv_pct*100)}% de primo-votants "
        f"et un niveau d'éducation de {education_level:.1f}, "
        f"la méthode '{least_inclusive}' entraîne {round(worst_nr*100, 1)}% de bulletins nuls "
        f"contre {round(plurality_nr*100, 1)}% pour Plurality. "
        f"Ce n'est pas l'électeur qui échoue — c'est la conception du bulletin."
    )

    return {
        "results":                results,
        "candidate_count_curve":  candidate_count_curve,
        "most_inclusive_method":  most_inclusive,
        "least_inclusive_method": least_inclusive,
        "pedagogical_note":       note,
    }, 200


# ── Shy Voter Effect ──────────────────────────────────────────────────────────

def _shy_voter_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /shy-voter — extracted for FastAPI v2 reuse.

    Simulate the Bradley / Shy Tory effect: voters who intend to vote for a
    socially 'sensitive' candidate declare a more acceptable preference in polls
    (with probability social_desirability_factor) but vote sincerely in the booth.
    """
    num_voters     = max(50,  min(500, int(data.get("num_voters",                  300))))
    ideology       = str(data.get("ideology",                  "random"))
    seed           = int(data.get("seed",                       42))
    shy_idx        = max(0,   int(data.get("shy_candidate_idx",  0)))
    sdf            = max(0.0, min(1.0, float(data.get("social_desirability_factor", 0.4))))
    num_polls      = max(3,   min(30,  int(data.get("num_polls",                   10))))
    cand_specs     = data.get("candidates", [
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
    shy_idx       = min(shy_idx, len(cand_names) - 1)
    shy_candidate = cand_names[shy_idx]
    all_ids       = [v["id"] for v in voters]

    # ── Sincere votes ─────────────────────────────────────────────────────
    sincere_votes: Dict[int, str] = {
        v["id"]: max(sincere_utilities[v["id"]], key=lambda k: sincere_utilities[v["id"]][k])
        for v in voters
    }
    real_counts = Counter(sincere_votes.values())
    real_results: Dict[str, float] = {
        c: round(real_counts.get(c, 0) / num_voters, 4) for c in cand_names
    }
    real_winner: str = max(real_results, key=real_results.__getitem__)

    # ── Second choices for shy voters ─────────────────────────────────────
    second_choices: Dict[int, str] = {}
    for v in voters:
        vid = v["id"]
        order = sorted(sincere_utilities[vid].keys(),
                       key=lambda k: -sincere_utilities[vid][k])
        sc = next((c for c in order if c != shy_candidate),
                  cand_names[(shy_idx + 1) % len(cand_names)])
        second_choices[vid] = sc

    # ── Declared votes (with shy masking) ────────────────────────────────
    decl_rng = _random.Random(seed + 1)
    declared: Dict[int, str] = {}
    for v in voters:
        vid = v["id"]
        s   = sincere_votes[vid]
        if s == shy_candidate and decl_rng.random() < sdf:
            declared[vid] = second_choices[vid]
        else:
            declared[vid] = s

    # ── Simulate polls ────────────────────────────────────────────────────
    poll_sample_size = min(1000, num_voters)
    poll_rng         = _random.Random(seed + 2)
    poll_results_out: list[Dict[str, Any]] = []

    for n in range(num_polls):
        sample    = [poll_rng.choice(all_ids) for _ in range(poll_sample_size)]
        dec_count = Counter(declared[vid] for vid in sample)
        predicted = {c: round(dec_count.get(c, 0) / poll_sample_size, 4) for c in cand_names}
        poll_results_out.append({
            "poll_n":    n + 1,
            "predicted": predicted,
            "real":      real_results,
        })

    # ── Average poll prediction + winner ─────────────────────────────────
    avg_pred: Dict[str, float] = {
        c: round(sum(pr["predicted"][c] for pr in poll_results_out) / num_polls, 4)
        for c in cand_names
    }
    poll_winner: str = max(avg_pred, key=avg_pred.__getitem__)
    polls_wrong       = poll_winner != real_winner

    systematic_error: Dict[str, float] = {
        c: round(avg_pred[c] - real_results[c], 4) for c in cand_names
    }

    # ── Social desirability curve (analytical → exactly monotone) ─────────
    real_shy_rate  = real_results.get(shy_candidate, 0.0)
    other_cands    = [c for c in cand_names if c != shy_candidate]
    other_total    = sum(real_results.get(c, 0) for c in other_cands) or 1.0

    curve: list[Dict[str, Any]] = []
    for step in range(11):
        f               = round(step / 10, 1)
        poll_shy        = real_shy_rate * (1.0 - f)
        poll_error_f    = round(real_shy_rate - poll_shy, 4)   # = real_shy_rate × f
        poll_others     = {
            c: real_results.get(c, 0) + real_shy_rate * f * (real_results.get(c, 0) / other_total)
            for c in other_cands
        }
        poll_f          = {shy_candidate: poll_shy, **poll_others}
        poll_win_f      = max(poll_f, key=poll_f.__getitem__)
        winner_wrong_f  = 1.0 if poll_win_f != real_winner else 0.0
        curve.append({
            "factor":           f,
            "poll_error":       poll_error_f,
            "winner_wrong_pct": winner_wrong_f,
        })

    # ── Pedagogical note ──────────────────────────────────────────────────
    shy_err = abs(systematic_error.get(shy_candidate, 0.0))
    note = (
        f"Avec un facteur de désirabilité sociale de {sdf}, "
        f"le candidat '{shy_candidate}' est sous-estimé de "
        f"{round(shy_err * 100, 1)}% en moyenne dans les sondages. "
    )
    if polls_wrong:
        note += f"Les sondages prédisaient '{poll_winner}' mais '{real_winner}' a gagné."
    else:
        note += f"Malgré le biais, les sondages prédisent correctement '{real_winner}'."

    return {
        "real_winner":               real_winner,
        "poll_winner":               poll_winner,
        "polls_wrong":               polls_wrong,
        "shy_candidate":             shy_candidate,
        "poll_results":              poll_results_out,
        "systematic_error":          systematic_error,
        "real_results":              real_results,
        "avg_poll_results":          avg_pred,
        "social_desirability_curve": curve,
        "pedagogical_note":          note,
    }, 200


# ── Electoral Fatigue ─────────────────────────────────────────────────────────

def _electoral_fatigue_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /electoral-fatigue — extracted for FastAPI v2 reuse.

    Simulate electoral fatigue across repeated elections.
    P(vote | election k) = max(engaged_pct, 1 - k × fatigue_rate)  [k = 0-based]
    Engaged voters (top engaged_pct by max_utility) always participate.
    As casual voters drop out, the residual electorate drifts ideologically
    toward the engaged (more partisan) voters.
    """
    num_voters     = max(50,  min(500,  int(data.get("num_voters",          200))))
    ideology       = str(data.get("ideology",          "random"))
    seed           = int(data.get("seed",               42))
    num_elections  = max(1,   min(12,   int(data.get("num_elections",         6))))
    fatigue_rate   = max(0.0, min(0.15, float(data.get("fatigue_rate",        0.07))))
    engaged_pct    = max(0.05, min(0.5, float(data.get("engaged_voter_pct",   0.2))))
    primary_method = str(data.get("method",            "plurality"))
    cand_specs     = data.get("candidates", [
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
    all_ids: list[int] = [v["id"] for v in voters]

    # ── Voter ideology positions (1D economy axis) ────────────────────────
    voter_ideo: Dict[int, float] = {
        v["id"]: round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3)
        for v in voters
    }
    full_mean_ideo = round(sum(voter_ideo.values()) / num_voters, 4)

    # ── Engaged voters = top engaged_pct by max_utility ──────────────────
    voter_max_util: Dict[int, float] = {
        v["id"]: max(sincere_utilities[v["id"]].values()) for v in voters
    }
    n_engaged      = max(1, round(engaged_pct * num_voters))
    engaged_ids: set[Any] = set(
        sorted(all_ids, key=lambda vid: -voter_max_util[vid])[:n_engaged]
    )
    partisan_threshold = 0.7  # "very partisan" label
    partisan_ids: set[Any] = {vid for vid, mu in voter_max_util.items() if mu > partisan_threshold}

    # ── Fast winner per method ────────────────────────────────────────────
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner   as _bw,
        get_irv_winner     as _iw,
        get_schulze_winner as _sw,
    )

    def _fast_winner(vlist: list[Dict[str, Any]]) -> tuple[Optional[str], Dict[str, float]]:
        if not vlist:
            return cand_names[0], {c: 0.0 for c in cand_names}
        rnk = [
            sorted(sincere_utilities[v["id"]].keys(),
                   key=lambda n: -sincere_utilities[v["id"]][n])
            for v in vlist
        ]
        if primary_method == "borda":
            w: Optional[str] = _bw(rnk)
        elif primary_method == "irv":
            w = _iw(rnk)
        elif primary_method == "schulze":
            w = _sw(rnk)
        elif primary_method == "approval":
            tally: Counter[Any] = Counter()
            for v in vlist:
                u  = sincere_utilities[v["id"]]
                th = sum(u.values()) / len(u) if u else 0.5
                for cname, val in u.items():
                    if val > th:
                        tally[cname] += 1
            w = max(tally, key=tally.__getitem__) if tally else cand_names[0]
        else:
            w = get_plurality_winner(rnk)
        total  = len(vlist)
        fc     = Counter(r[0] for r in rnk)
        shares = {c: round(fc.get(c, 0) / total, 4) for c in cand_names}
        return w, shares

    # ── Simulate successive elections ─────────────────────────────────────
    rng_fat = _random.Random(seed + 500)
    elections_out: list[Dict[str, Any]] = []

    for k in range(num_elections):
        p_vote = max(engaged_pct, 1.0 - k * fatigue_rate)

        actual_voters = [
            v for v in voters
            if v["id"] in engaged_ids or rng_fat.random() < p_vote
        ]
        n_act   = len(actual_voters)
        turnout = round(n_act / num_voters, 4)
        winner, vote_shares = _fast_winner(actual_voters)

        if actual_voters:
            act_ids   = [v["id"] for v in actual_voters]
            mean_ideo = round(sum(voter_ideo[vid] for vid in act_ids) / n_act, 4)
            part_cnt  = sum(1 for vid in act_ids if vid in partisan_ids)
            part_pct  = round(part_cnt / n_act, 4)
        else:
            mean_ideo = 0.0
            part_pct  = 0.0

        elections_out.append({
            "election_n": k + 1,
            "turnout":    turnout,
            "winner":     winner,
            "voter_profile": {
                "mean_ideology_x": mean_ideo,
                "partisan_pct":    part_pct,
            },
            "vote_shares": vote_shares,
        })

    # ── Summary stats ─────────────────────────────────────────────────────
    winner_drift = [e["winner"] for e in elections_out]
    first_winner = winner_drift[0] if winner_drift else cand_names[0]
    winner_changed_at: Optional[int] = next(
        (e["election_n"] for e in elections_out if e["winner"] != first_winner),
        None,
    )

    first_ideo = elections_out[0]["voter_profile"]["mean_ideology_x"] if elections_out else 0.0
    last_ideo  = elections_out[-1]["voter_profile"]["mean_ideology_x"] if elections_out else 0.0
    ideology_drift    = round(last_ideo - first_ideo, 4)
    representation_gap = round(last_ideo - full_mean_ideo, 4)

    note = (
        f"Au bout de {num_elections} élections avec un taux de fatigue de "
        f"{round(fatigue_rate * 100)}%, la participation tombe à "
        f"{round(elections_out[-1]['turnout'] * 100, 1)}%. "
        f"La position idéologique moyenne des votants dérive de "
        f"{ideology_drift:+.3f} par rapport à la 1ère élection "
        f"(écart de représentation : {representation_gap:+.3f})."
    )

    return {
        "elections":             elections_out,
        "winner_drift":          winner_drift,
        "winner_changed_at":     winner_changed_at,
        "ideology_drift":        ideology_drift,
        "representation_gap":    representation_gap,
        "full_mean_ideology":    full_mean_ideo,
        "pedagogical_note":      note,
    }, 200


# ── Choice Overload ───────────────────────────────────────────────────────────

def _choice_overload_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /choice-overload — extracted for FastAPI v2 reuse."""
    num_voters         = max(50,  min(300, int(data.get("num_voters",         150))))
    ideology           = str(data.get("ideology",         "random"))
    seed               = int(data.get("seed",              42))
    cand_counts        = sorted({max(2, min(15, n)) for n in
                                 data.get("candidate_counts", [2, 3, 5, 7, 10])})[:8]
    overload_threshold = max(2,   min(12, int(data.get("overload_threshold",    5))))
    hw                 = data.get("heuristic_weights", {})
    h_not              = max(0.0, min(1.0, float(hw.get("notoriety",  0.20))))
    h_pri              = max(0.0, min(1.0, float(hw.get("primacy",    0.10))))
    h_par              = max(0.0, min(1.0, float(hw.get("partisan",   0.20))))
    total_h            = min(1.0, h_not + h_pri + h_par)
    # Pydantic Optional[List[str]] may pass null — fall back to the default.
    methods_req        = (data.get("methods") or ["plurality", "approval",
                                                   "borda", "majority_judgment"])[:5]

    if not cand_counts:
        return {"error": "candidate_counts must be non-empty"}, 400

    from api.engine.utils.simulation_score_utils import get_majority_judgment_winner as _mj_co
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner   as _bw_co,
        get_irv_winner     as _iw_co,
        get_schulze_winner as _sw_co,
    )

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    # ── Fixed electorate (voters same across all N) ───────────────────────
    voters = [
        create_voter(issues, i, ideology_distribution=ideology)
        for i in range(num_voters)
    ]
    voter_ideo: Dict[int, float] = {
        v["id"]: 2.0 * v["issue_positions"].get("economy", 0.5) - 1.0
        for v in voters
    }

    def _quick_winner_co(
        method: str,
        v_list: list[Dict[str, Any]],
        rnk:    list[list[str]],
        utils:  Dict[Any, Dict[str, float]],
        voted:  Dict[int, str],
        is_h:   Dict[int, bool],
        cnames: list[str],
    ) -> Optional[str]:
        if not v_list:
            return cnames[0] if cnames else None
        if method == "plurality":
            t: Counter[Any] = Counter(voted[v["id"]] for v in v_list)
            return max(t, key=t.__getitem__) if t else cnames[0]
        if method == "borda":
            return _bw_co(rnk)
        if method == "irv":
            return _iw_co(rnk)
        if method == "schulze":
            return _sw_co(rnk)
        if method == "approval":
            t2: Counter[Any] = Counter()
            for v in v_list:
                vid = v["id"]
                if is_h[vid]:
                    t2[voted[vid]] += 1
                else:
                    u   = utils[vid]
                    th2 = sum(u.values()) / len(u) if u else 0.5
                    for cn, val in u.items():
                        if val > th2:
                            t2[cn] += 1
            return max(t2, key=t2.__getitem__) if t2 else cnames[0]
        if method == "majority_judgment":
            mj_u = [dict(utils[v["id"]]) for v in v_list]
            try:
                r = _mj_co(mj_u)
                return str(r["winner"]) if r.get("winner") else cnames[0]
            except Exception:
                return get_plurality_winner(rnk)
        return get_plurality_winner(rnk)

    # ── Main loop across N ────────────────────────────────────────────────
    results_by_n: list[Dict[str, Any]] = []
    regret_curve: list[Dict[str, Any]] = []
    sincere_match: Dict[str, int] = {m: 0 for m in methods_req}
    n_overload_cases = 0

    for n in cand_counts:
        # Deterministic candidates for this n
        c_rng   = _random.Random(seed + n * 1000)
        c_specs = [
            {
                "name": chr(65 + i) if i < 26 else f"C{i}",
                "x":    c_rng.uniform(-1, 1),
                "y":    c_rng.uniform(-1, 1),
            }
            for i in range(n)
        ]
        cands_n  = [
            _build_candidate_from_xy(
                i, str(c_specs[i]["name"]),
                max(-1.0, min(1.0, float(str(c_specs[i]["x"])))),
                max(-1.0, min(1.0, float(str(c_specs[i]["y"])))),
                issues,
            )
            for i in range(n)
        ]
        cnames_n = [c["name"] for c in cands_n]
        cideo_n  = {c["name"]: round(2.0 * float(c["ideology_position"]) - 1.0, 3)
                    for c in cands_n}

        # Utilities (deterministic)
        utils_n: Dict[Any, Dict[str, float]] = {
            v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"]
                      for c in cands_n}
            for v in voters
        }

        # Sincere votes (argmax utility)
        sinc_vote: Dict[int, str] = {
            v["id"]: max(utils_n[v["id"]], key=lambda k: utils_n[v["id"]][k])
            for v in voters
        }

        # Heuristic assignment
        h_rng  = _random.Random(seed + n * 5000 + 777)
        voted:  Dict[int, str]  = {}
        is_h:   Dict[int, bool] = {}

        for v in voters:
            vid = v["id"]
            if n > overload_threshold:
                r = h_rng.random()
                if r < h_not:
                    voted[vid], is_h[vid] = cnames_n[0], True
                elif r < h_not + h_pri:
                    voted[vid], is_h[vid] = cnames_n[0], True
                elif r < total_h:
                    partisan_cand = min(cnames_n,
                                       key=lambda c: abs(voter_ideo[vid] - cideo_n[c]))
                    voted[vid], is_h[vid] = partisan_cand, True
                else:
                    voted[vid], is_h[vid] = sinc_vote[vid], False
            else:
                voted[vid], is_h[vid] = sinc_vote[vid], False

        heuristic_pct = round(sum(is_h.values()) / num_voters, 4)

        # Voter regret
        regrets_n = [
            max(utils_n[v["id"]].values()) - utils_n[v["id"]].get(voted[v["id"]], 0)
            for v in voters
        ]
        mean_regret = round(sum(regrets_n) / len(regrets_n), 6) if regrets_n else 0.0

        # Rankings (heuristic choice first, rest sincere)
        h_rnk: list[list[str]] = []
        s_rnk: list[list[str]] = []
        for v in voters:
            vid      = v["id"]
            sorder   = sorted(utils_n[vid].keys(), key=lambda k: -utils_n[vid][k])
            hchoice  = voted[vid]
            s_rnk.append(sorder)
            if hchoice != sorder[0]:
                h_rnk.append([hchoice] + [c for c in sorder if c != hchoice])
            else:
                h_rnk.append(sorder)

        # Run methods (heuristic vs. sincere)
        winner_by_method:      Dict[str, Optional[str]] = {}
        sinc_winner_by_method: Dict[str, Optional[str]] = {}
        s_voted = {v["id"]: sinc_vote[v["id"]] for v in voters}
        s_is_h  = {v["id"]: False for v in voters}

        for meth in methods_req:
            winner_by_method[meth]      = _quick_winner_co(meth, voters, h_rnk, utils_n, voted,   is_h,   cnames_n)
            sinc_winner_by_method[meth] = _quick_winner_co(meth, voters, s_rnk, utils_n, s_voted, s_is_h, cnames_n)
            if n > overload_threshold:
                if winner_by_method[meth] == sinc_winner_by_method[meth]:
                    sincere_match[meth] += 1

        if n > overload_threshold:
            n_overload_cases += 1

        condorcet_w = get_condorcet_winner(s_rnk)

        results_by_n.append({
            "num_candidates":        n,
            "mean_voter_regret":     mean_regret,
            "heuristic_voters":      heuristic_pct,
            "winner_by_method":      winner_by_method,
            "condorcet_winner":      condorcet_w,
            "methods_elect_condorcet": {
                m: winner_by_method[m] == condorcet_w for m in methods_req
            },
        })
        regret_curve.append({"n_candidates": n, "regret": mean_regret})

    # ── Robustness ranking ────────────────────────────────────────────────
    if n_overload_cases > 0:
        match_rates = {m: sincere_match[m] / n_overload_cases for m in methods_req}
    else:
        match_rates = {m: 1.0 for m in methods_req}

    most_robust  = max(match_rates, key=match_rates.__getitem__)
    least_robust = min(match_rates, key=match_rates.__getitem__)

    # ── Pedagogical note ──────────────────────────────────────────────────
    over_regrets = [r["regret"] for r in regret_curve
                    if r["n_candidates"] > overload_threshold]
    avg_over_regret = round(sum(over_regrets) / len(over_regrets), 4) if over_regrets else 0.0
    note = (
        f"Au-delà de {overload_threshold} candidats, "
        f"{round(total_h * 100)}% des électeurs utilisent une heuristique "
        f"(notoriété, primauté ou partisane). "
        f"Le regret moyen de vote est de {round(avg_over_regret * 100, 1)} points d'utilité. "
        f"'{most_robust}' est la méthode la plus robuste à la surcharge cognitive."
    )

    return {
        "results_by_n":         results_by_n,
        "regret_curve":         regret_curve,
        "most_robust_method":   most_robust,
        "least_robust_method":  least_robust,
        "overload_threshold":   overload_threshold,
        "heuristic_weights":    {"notoriety": h_not, "primacy": h_pri, "partisan": h_par},
        "pedagogical_note":     note,
    }, 200

