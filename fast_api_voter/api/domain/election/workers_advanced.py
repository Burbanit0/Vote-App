"""
api.domain.election.workers_advanced — governance / advanced-mechanism workers,
split out of the workers.py monolith (incremental decomposition).

Pure `data: dict -> (body, http_status)` workers: demographic turnout,
compulsory voting, sortition, party dynamics, deliberation, power indices.
Depends only on the engine utils + the shared ._electorate / ._helpers.
"""
from __future__ import annotations

import itertools
import math
import random as _random
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

import numpy as _np

from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.simulation_voting_utils import calculate_utility, create_voter
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.simulation_ranked_utils import (
    get_borda_winner, get_condorcet_winner, get_irv_winner, get_plurality_winner,
    get_schulze_winner,
)
from ._electorate import _build_base_electorate
from ._helpers import build_candidate_from_xy as _build_candidate_from_xy


# ── Demographic Turnout ───────────────────────────────────────────────────────

_AGE_LABELS  = ["jeunes (18-34)", "adultes (35-64)", "seniors (65+)"]
_EDU_LABELS  = ["faible éducation", "éducation élevée"]

_DT_RULES = {
    "borda":   get_borda_winner,
    "irv":     get_irv_winner,
    "schulze": get_schulze_winner,
}

_DT_DEFAULT_CANDIDATES = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.1},
]


def _dt_floats(raw: Any, default: List[float], keep: int) -> List[float]:
    """One profile vector: the caller's numbers when given, this endpoint's
    defaults otherwise. Pydantic passes null for an omitted Optional, so an
    empty value has to fall back too — hence `or`, not a dict default."""
    return [float(x) for x in (raw or default)][:keep]


def _dt_profile(dp: Dict[str, Any]) -> Dict[str, List[float]]:
    """The demographic profile with defaults filled in, the two population
    splits renormalised to sum to 1."""
    prof = {
        "age_dist": _dt_floats(dp.get("age_distribution"),       [0.25, 0.45, 0.30], 3),
        "to_age":   _dt_floats(dp.get("turnout_by_age"),         [0.55, 0.70, 0.85], 3),
        "ideo_age": _dt_floats(dp.get("ideology_by_age"),        [-0.10, 0.00, 0.15], 3),
        "edu_dist": _dt_floats(dp.get("education_distribution"), [0.40, 0.60], 2),
        "to_edu":   _dt_floats(dp.get("turnout_by_education"),   [1.00, 1.00], 2),
        "ideo_edu": _dt_floats(dp.get("ideology_by_education"),  [0.05, -0.05], 2),
    }
    for key in ("age_dist", "edu_dist"):
        total = sum(prof[key]) or 1.0
        prof[key] = [x / total for x in prof[key]]
    return prof


def _dt_candidates(
    cand_specs: List[Dict[str, Any]],
    issues: Any,
) -> tuple[List[str], List[Dict[str, Any]]]:
    """Names and spatial candidates, positions clamped to the unit square."""
    names = [str(s.get("name", f"C{i}")) for i, s in enumerate(cand_specs)]
    candidates = [
        _build_candidate_from_xy(
            i, names[i],
            max(-1.0, min(1.0, float(s.get("x", 0.0)))),
            max(-1.0, min(1.0, float(s.get("y", 0.0)))),
            issues,
        )
        for i, s in enumerate(cand_specs)
    ]
    return names, candidates


def _dt_pick_group(rng_val: float, cumsum: List[float]) -> int:
    """Index of the band `rng_val` falls in, given cumulative shares."""
    for i, th in enumerate(cumsum):
        if rng_val < th:
            return i
    return len(cumsum) - 1


def _dt_assign_demographics(
    raw_voters: List[Dict[str, Any]],
    seed: int,
    prof: Dict[str, List[float]],
) -> Dict[Any, Dict[str, Any]]:
    """Give each voter an age band, an education band, an ideology shifted by
    both, and the turnout probability those bands imply. Also rewrites the
    voter's economy position, since that is what the utility model reads."""
    demo_rng   = _random.Random(seed)
    age_cumsum = [sum(prof["age_dist"][:k+1]) for k in range(len(prof["age_dist"]))]
    edu_cumsum = [sum(prof["edu_dist"][:k+1]) for k in range(len(prof["edu_dist"]))]

    voter_demo: Dict[Any, Dict[str, Any]] = {}
    for v in raw_voters:
        ag   = _dt_pick_group(demo_rng.random(), age_cumsum)
        eg   = _dt_pick_group(demo_rng.random(), edu_cumsum)
        base = demo_rng.uniform(-0.5, 0.5)
        ideo = max(-1.0, min(1.0, base + prof["ideo_age"][ag] + prof["ideo_edu"][eg]))
        p_v  = max(0.0, min(1.0, prof["to_age"][ag] * prof["to_edu"][eg]))
        voter_demo[v["id"]] = {"age": ag, "edu": eg, "ideology": ideo, "p_vote": p_v}
        v["issue_positions"]["economy"] = (ideo + 1.0) / 2.0   # remap to [0, 1]
    return voter_demo


def _dt_turnout_draw(
    raw_voters: List[Dict[str, Any]],
    voter_demo: Dict[Any, Dict[str, Any]],
    seed: int,
) -> tuple[set[Any], List[Dict[str, Any]]]:
    """Who actually shows up: one draw per voter against their own probability."""
    t_rng = _random.Random(seed + 100)
    voted_ids: set[Any] = {
        v["id"] for v in raw_voters
        if t_rng.random() < voter_demo[v["id"]]["p_vote"]
    }
    return voted_ids, [v for v in raw_voters if v["id"] in voted_ids]


def _dt_winner(
    vlist: List[Dict[str, Any]],
    utils: Dict[Any, Dict[str, float]],
    cand_names: List[str],
    method: str,
) -> tuple[str, Dict[str, float]]:
    """Winner and first-choice shares for one voter subset."""
    if not vlist:
        return cand_names[0], {c: 0.0 for c in cand_names}
    rnk = [sorted(utils[v["id"]].keys(), key=lambda n: -utils[v["id"]][n]) for v in vlist]
    w: Optional[str] = _DT_RULES.get(method, get_plurality_winner)(rnk)
    fc = Counter(r[0] for r in rnk)
    shares = {c: round(fc.get(c, 0) / len(vlist), 4) for c in cand_names}
    return w or cand_names[0], shares


def _dt_mean(
    voters: List[Dict[str, Any]],
    voter_demo: Dict[Any, Dict[str, Any]],
    field: str,
) -> float:
    """Mean of one demographic field over a voter subset; 0.0 when empty.
    `field` is an age or education band (int) or an ideology (float), so the
    values are widened to float before summing."""
    if not voters:
        return 0.0
    return round(sum(float(voter_demo[v["id"]][field]) for v in voters) / len(voters), 4)


def _dt_breakdown(
    raw_voters: List[Dict[str, Any]],
    voted_ids: set[Any],
    voter_demo: Dict[Any, Dict[str, Any]],
    prof: Dict[str, List[float]],
    num_voters: int,
    n_actual: int,
) -> List[Dict[str, Any]]:
    """One row per age × education cell: its share of the population, its share
    of the people who actually voted, and the mean ideology of the latter."""
    grp_pop: Dict[tuple[Any, ...], int] = {}
    grp_vot: Dict[tuple[Any, ...], int] = {}
    grp_ideo: Dict[tuple[Any, ...], list[Any]] = {}
    for v in raw_voters:
        d   = voter_demo[v["id"]]
        key = (d["age"], d["edu"])
        grp_pop[key] = grp_pop.get(key, 0) + 1
        if v["id"] in voted_ids:
            grp_vot[key] = grp_vot.get(key, 0) + 1
            grp_ideo.setdefault(key, []).append(d["ideology"])

    breakdown: List[Dict[str, Any]] = []
    for ag in range(len(prof["age_dist"])):
        for eg in range(len(prof["edu_dist"])):
            key       = (ag, eg)
            ideo_vals = grp_ideo.get(key, [])
            breakdown.append({
                "group":          f"{_AGE_LABELS[ag]}, {_EDU_LABELS[eg]}",
                "population_pct": round(grp_pop.get(key, 0) / num_voters, 4),
                "voter_pct":      round(grp_vot.get(key, 0) / n_actual, 4) if n_actual else 0.0,
                "ideology_mean":  round(sum(ideo_vals) / len(ideo_vals), 4) if ideo_vals else 0.0,
            })
    return breakdown


def _dt_winners_by_method(
    subsets: List[List[Dict[str, Any]]],
    candidates: List[Dict[str, Any]],
    issues: Any,
) -> List[Dict[str, Any]]:
    """Winner per method for each voter subset. All-or-nothing on failure, kept
    from before the split: the two subsets must never disagree about whether the
    comparison ran at all, or the caller would read one as a real change."""
    try:
        compares = [compare_all_methods(vs, candidates, issues) for vs in subsets]
    except Exception:  # pylint: disable=broad-except
        return [{} for _ in subsets]
    return [
        {m: d.get("winner") for m, d in c.get("methods", {}).items()}
        for c in compares
    ]


# A cell counts as over- or under-represented once its share of the people who
# actually voted is this far from its share of the population.
_DT_REPRESENTATION_MARGIN = 0.05


def _dt_representation_gap(
    breakdown: List[Dict[str, Any]],
    ideo_drift: float,
) -> Dict[str, Any]:
    """Which demographic cells the turnout bias lifted, and which it dropped."""
    return {
        "ideology_drift": ideo_drift,
        "overrepresented_groups": [
            d["group"] for d in breakdown
            if d["voter_pct"] > d["population_pct"] + _DT_REPRESENTATION_MARGIN
        ],
        "underrepresented_groups": [
            d["group"] for d in breakdown
            if d["voter_pct"] < d["population_pct"] - _DT_REPRESENTATION_MARGIN
        ],
    }


def _dt_note(
    n_actual: int,
    num_voters: int,
    ideo_drift: float,
    biased_winner: str,
    corrected_winner: str,
) -> str:
    note = (
        f"Avec les taux de participation configurés, "
        f"l'électorat effectif ({round(n_actual/num_voters*100, 1)}% de participation) "
        f"est décalé de {ideo_drift:+.3f} sur l'axe idéologique par rapport à la population totale. "
    )
    if biased_winner != corrected_winner:
        return note + f"Si tous votaient, le résultat serait différent : '{biased_winner}' → '{corrected_winner}'."
    return note + f"La méthode produit le même vainqueur ('{biased_winner}') malgré le biais de participation."


def _demographic_turnout_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /demographic-turnout — extracted for FastAPI v2."""
    num_voters     = max(50, min(500, int(data.get("num_voters", 300))))
    seed           = int(data.get("seed", 42))
    primary_method = str(data.get("method", "plurality"))
    correct_flag   = bool(data.get("correct_for_turnout", True))
    cand_specs     = data.get("candidates", _DT_DEFAULT_CANDIDATES)[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    prof = _dt_profile(data.get("demographic_profile") or {})

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES
    cand_names, candidates = _dt_candidates(cand_specs, issues)

    raw_voters = [
        create_voter(issues, i, ideology_distribution="random")
        for i in range(num_voters)
    ]
    voter_demo = _dt_assign_demographics(raw_voters, seed, prof)

    # Utilities are computed after the ideology override, not before.
    utils: Dict[Any, Dict[str, float]] = {
        v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"] for c in candidates}
        for v in raw_voters
    }

    voted_ids, actual_voters = _dt_turnout_draw(raw_voters, voter_demo, seed)
    n_actual = len(actual_voters)

    biased_winner, biased_shares = _dt_winner(actual_voters, utils, cand_names, primary_method)
    corrected_winner, corrected_shares = (
        _dt_winner(raw_voters, utils, cand_names, primary_method) if correct_flag
        else (biased_winner, biased_shares)
    )

    full_mean  = _dt_mean(raw_voters, voter_demo, "ideology")
    bias_mean  = _dt_mean(actual_voters, voter_demo, "ideology")
    ideo_drift = round(bias_mean - full_mean, 4)

    breakdown = _dt_breakdown(
        raw_voters, voted_ids, voter_demo, prof, num_voters, n_actual,
    )
    biased_by_method, corrected_by_method = _dt_winners_by_method(
        [actual_voters, raw_voters], candidates, issues,
    )

    return {
        "biased_result": {
            "winner":         biased_winner,
            "vote_shares":    biased_shares,
            "actual_turnout": round(n_actual / num_voters, 4),
            "voter_profile": {
                "mean_age_group":       _dt_mean(actual_voters, voter_demo, "age"),
                "mean_education_level": _dt_mean(actual_voters, voter_demo, "edu"),
                "mean_ideology_x":      bias_mean,
            },
            "winners_by_method": biased_by_method,
        },
        "corrected_result": {
            "winner":         corrected_winner,
            "vote_shares":    corrected_shares,
            "mean_ideology_x": full_mean,
            "winners_by_method": corrected_by_method,
        },
        "winner_changed":      biased_winner != corrected_winner,
        "representation_gap":  _dt_representation_gap(breakdown, ideo_drift),
        "demographic_breakdown": breakdown,
        "pedagogical_note":      _dt_note(
            n_actual, num_voters, ideo_drift, biased_winner, corrected_winner,
        ),
    }, 200


# ── Compulsory Voting ─────────────────────────────────────────────────────────

_COMPULSORY_BIAS = 0.15   # rightward participation bias in voluntary elections


def _compulsory_voting_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /compulsory-voting — extracted for FastAPI v2.

    Simulate voluntary vs. compulsory voting on the same electorate.
    Voluntary turnout is right-biased (empirical pattern: conservative voters
    participate more), while compulsory elections add reluctant left-leaning
    voters who may vote null, randomly, or sincerely.
    """
    num_voters   = max(50,  min(500, int(data.get("num_voters",          300))))
    ideology     = str(data.get("ideology",           "random"))
    seed         = int(data.get("seed",                42))
    vol_to       = max(0.30, min(0.90, float(data.get("voluntary_turnout",   0.65))))
    comp_to      = max(0.70, min(0.99, float(data.get("compulsory_turnout",  0.92))))
    rel_null     = max(0.00, min(0.20, float(data.get("reluctant_null_rate",  0.04))))
    rel_rnd      = max(0.00, min(1.00, float(data.get("reluctant_random_pct", 0.08))))
    str(data.get("method", "plurality"))
    cand_specs   = data.get("candidates", [
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
    voter_ideo:     Dict[int, float] = {
        v["id"]: round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3)
        for v in voters
    }
    voter_max_util: Dict[int, float] = {
        v["id"]: max(sincere_utilities[v["id"]].values()) for v in voters
    }
    full_mean_ideo = round(sum(voter_ideo.values()) / num_voters, 4)

    # ── Participation scores (fixed per seed) ─────────────────────────────
    part_rng = _random.Random(seed)
    part_score: Dict[int, float] = {v["id"]: part_rng.random() for v in voters}

    # Voluntary: right-leaning voters have higher effective threshold
    # Compulsory: same bias, higher base threshold
    voluntary_ids:  set[Any] = {
        vid for vid, sc in part_score.items()
        if sc < vol_to + _COMPULSORY_BIAS * voter_ideo[vid]
    }
    compulsory_ids: set[Any] = {
        vid for vid, sc in part_score.items()
        if sc < comp_to + _COMPULSORY_BIAS * voter_ideo[vid]
    }
    reluctant_ids: set[Any] = compulsory_ids - voluntary_ids

    # ── Sincere votes ─────────────────────────────────────────────────────
    sincere_vote: Dict[int, str] = {
        v["id"]: max(sincere_utilities[v["id"]], key=lambda k: sincere_utilities[v["id"]][k])
        for v in voters
    }

    # ── Compulsory vote assignment ────────────────────────────────────────
    _NULL  = "__NULL__"
    noise_rng   = _random.Random(seed + 200)
    comp_vote:  Dict[int, str] = {}
    null_count  = 0
    rnd_count   = 0

    for vid in compulsory_ids:
        if vid in reluctant_ids:
            r = noise_rng.random()
            if r < rel_null:
                comp_vote[vid] = _NULL
                null_count += 1
            elif r < rel_null + rel_rnd:
                comp_vote[vid] = noise_rng.choice(cand_names)
                rnd_count += 1
            else:
                comp_vote[vid] = sincere_vote[vid]
        else:
            comp_vote[vid] = sincere_vote[vid]

    # ── Election runner (plurality) ───────────────────────────────────────
    def _run(vote_dict: Dict[int, str], voter_set: set[Any]) -> tuple[str, Dict[str, float], float]:
        tally: Counter[Any] = Counter()
        n_null = sum(1 for vid in voter_set if vote_dict.get(vid, _NULL) == _NULL)
        for vid in voter_set:
            v = vote_dict.get(vid, sincere_vote[vid])
            if v != _NULL:
                tally[v] += 1
        n_valid = len(voter_set) - n_null
        winner  = max(tally, key=tally.__getitem__) if tally else cand_names[0]
        shares  = {
            c: round(tally.get(c, 0) / n_valid, 4) if n_valid else 0.0
            for c in cand_names
        }
        return winner, shares, round(n_null / len(voter_set), 4) if voter_set else 0.0

    vol_vote = {vid: sincere_vote[vid] for vid in voluntary_ids}
    vol_winner,  vol_shares,  vol_null  = _run(vol_vote, voluntary_ids)
    comp_winner, comp_shares, comp_null = _run(comp_vote, compulsory_ids)
    winner_changed = vol_winner != comp_winner

    # ── Statistics ────────────────────────────────────────────────────────
    n_vol  = len(voluntary_ids)
    n_comp = len(compulsory_ids)
    n_rel  = len(reluctant_ids)

    vol_mean  = round(sum(voter_ideo[vid] for vid in voluntary_ids)  / n_vol,  4) if n_vol  else 0.0
    comp_mean = round(sum(voter_ideo[vid] for vid in compulsory_ids) / n_comp, 4) if n_comp else 0.0

    vol_drift  = abs(vol_mean  - full_mean_ideo)
    comp_drift = abs(comp_mean - full_mean_ideo)
    representation_improvement = round(max(0.0, vol_drift - comp_drift), 4)

    n_valid_comp = n_comp - null_count
    noise_effect     = round(rnd_count / n_valid_comp, 4)  if n_valid_comp else 0.0
    quality_degradation = noise_effect

    partisan_thr = 0.7
    vol_partisan = sum(1 for vid in voluntary_ids if voter_max_util[vid] > partisan_thr)

    note = (
        f"Le vote obligatoire augmente la participation de "
        f"{round(n_vol/num_voters*100, 1)}% à {round(n_comp/num_voters*100, 1)}%, "
        f"ajoutant {n_rel} électeurs réticents. "
        f"Représentativité améliorée de {representation_improvement:.3f}, "
        f"mais {round(quality_degradation*100, 1)}% des votes compulsoires sont du bruit aléatoire."
    )

    # ── Per-method winners for both voter subsets (for central matrix diff) ──
    try:
        vol_voters  = [v for v in voters if v["id"] in voluntary_ids]
        comp_voters = [v for v in voters if v["id"] in compulsory_ids]
        vol_compare  = compare_all_methods(vol_voters,  candidates, issues)
        comp_compare = compare_all_methods(comp_voters, candidates, issues)
        vol_winners_by_method = {
            m: d.get("winner") for m, d in vol_compare.get("methods", {}).items()
        }
        comp_winners_by_method = {
            m: d.get("winner") for m, d in comp_compare.get("methods", {}).items()
        }
    except Exception:  # pylint: disable=broad-except
        vol_winners_by_method = {}
        comp_winners_by_method = {}

    return {
        "voluntary": {
            "turnout":     round(n_vol  / num_voters, 4),
            "winner":      vol_winner,
            "vote_shares": vol_shares,
            "null_rate":   vol_null,
            "voter_profile": {
                "mean_ideology_x": vol_mean,
                "partisan_pct":    round(vol_partisan / n_vol, 4) if n_vol else 0.0,
            },
            "winners_by_method": vol_winners_by_method,
        },
        "compulsory": {
            "turnout":          round(n_comp / num_voters, 4),
            "winner":           comp_winner,
            "vote_shares":      comp_shares,
            "null_rate":        comp_null,
            "reluctant_count":  n_rel,
            "noise_effect":     noise_effect,
            "winners_by_method": comp_winners_by_method,
        },
        "winner_changed":             winner_changed,
        "representation_improvement": representation_improvement,
        "quality_degradation":        quality_degradation,
        "pedagogical_note":           note,
    }, 200


# ── Sortition (tirage au sort) ────────────────────────────────────────────────


def _sortition_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /sortition — extracted for FastAPI v2 reuse."""
    num_voters      = max(50,  min(500, int(data.get("num_voters",        300))))
    assembly_size   = max(5,   min(300, int(data.get("assembly_size",      50))))
    ideology        = str(data.get("ideology",          "random"))
    seed            = int(data.get("seed",               42))
    str(data.get("method",            "plurality"))
    num_sims        = max(5,   min(100, int(data.get("num_simulations",   20))))
    realistic_cands = bool(data.get("realistic_candidates", True))
    cand_specs      = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    # Pydantic may pass null for the whole stratification object — guard.
    strat_cfg   = data.get("stratification") or {}
    age_dist_raw = strat_cfg.get("age_groups") or [0.25, 0.45, 0.30]
    bool(strat_cfg.get("gender_parity", True))
    edu_quota   = bool(strat_cfg.get("education_quota", True))

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    all_ids: list[int] = [v["id"] for v in voters]

    # ── Voter ideology + demographics ─────────────────────────────────────
    voter_ideo: Dict[int, float] = {
        v["id"]: round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3)
        for v in voters
    }
    full_mean_ideo = round(sum(voter_ideo.values()) / num_voters, 4)

    # Demographics (for stratified sortition)
    d_rng = _random.Random(seed + 50)
    age_sum  = sum(age_dist_raw) or 1.0
    age_dist = [x / age_sum for x in age_dist_raw[:3]]
    age_cum  = [sum(age_dist[:k+1]) for k in range(len(age_dist))]

    def _age_group(r: float) -> int:
        for i, th in enumerate(age_cum):
            if r < th:
                return i
        return len(age_cum) - 1

    voter_age: Dict[int, int] = {v["id"]: _age_group(d_rng.random()) for v in voters}
    voter_edu: Dict[int, int] = {v["id"]: (0 if d_rng.random() < 0.40 else 1) for v in voters}

    # ── Metric helpers ────────────────────────────────────────────────────
    def _representativity(asm: set[Any]) -> float:
        if not asm:
            return 0.0
        mean = sum(voter_ideo[vid] for vid in asm) / len(asm)
        return round(max(0.0, 1.0 - 2.0 * abs(mean - full_mean_ideo)), 4)

    def _diversity(asm: set[Any]) -> float:
        if not asm:
            return 0.0
        ideos = [voter_ideo[vid] for vid in asm]
        bins  = [-1.0, -0.5, 0.0, 0.5, 1.01]
        counts = [0] * 4
        for ideo in ideos:
            for i in range(4):
                if bins[i] <= ideo < bins[i + 1]:
                    counts[i] += 1
                    break
        n  = len(ideos)
        ps = [c / n for c in counts if c > 0]
        if len(ps) <= 1:
            return 0.0
        ent = -sum(p * math.log(p) for p in ps)
        return round(ent / math.log(4), 4)

    def _decision_regret(asm: set[Any]) -> float:
        if not asm:
            return 0.0
        asm_mean = sum(voter_ideo[vid] for vid in asm) / len(asm)
        return round(
            sum(abs(voter_ideo[vid] - asm_mean) for vid in all_ids) / num_voters, 4
        )

    def _gini_repr(asm: set[Any]) -> float:
        if not asm:
            return 0.0
        pop_s = sorted(voter_ideo.values())
        q     = max(1, num_voters // 4)
        bounds = [pop_s[0], pop_s[q], pop_s[2 * q], pop_s[3 * q], pop_s[-1] + 0.01]
        ideos  = [voter_ideo[vid] for vid in asm]
        n_asm  = len(ideos)
        ratios = []
        for i in range(4):
            af = sum(1 for x in ideos if bounds[i] <= x < bounds[i + 1]) / n_asm
            ratios.append(af / 0.25)
        s  = sorted(ratios)
        tot = sum(s) or 1.0
        cs  = sum((i + 1) * v for i, v in enumerate(s))
        return round(abs(2.0 * cs / (4 * tot) - (4 + 1) / 4), 4)

    def _asm_metrics(asm: set[Any]) -> Dict[str, Any]:
        n = len(asm)
        if n == 0:
            return {k: 0.0 for k in ("members_ideology_mean", "representativity",
                                      "diversity", "decision_regret", "gini_representation")}
        mean_ideo = round(sum(voter_ideo[vid] for vid in asm) / n, 4)
        return {
            "members_ideology_mean": mean_ideo,
            "representativity":      _representativity(asm),
            "diversity":             _diversity(asm),
            "decision_regret":       _decision_regret(asm),
            "gini_representation":   _gini_repr(asm),
            "demographic_profile": {
                "age":       round(sum(voter_age[vid] for vid in asm) / n, 4),
                "education": round(sum(voter_edu[vid] for vid in asm) / n, 4),
            },
        }

    # ── Assembly constructors ─────────────────────────────────────────────
    def _elected_asm(rng: _random.Random) -> set[Any]:
        cand_n = min(assembly_size * 3, num_voters)
        if realistic_cands:
            # Add noise so each MC run gets a slightly different candidate pool
            noisy_scores = {
                vid: abs(voter_ideo[vid]) + rng.uniform(0, 0.25)
                for vid in all_ids
            }
            pool_sorted = sorted(all_ids, key=lambda vid: -noisy_scores[vid])
            pool = set(pool_sorted[:cand_n])
        else:
            pool = set(rng.sample(all_ids, cand_n))

        tally: Counter[Any] = Counter()
        for vid in all_ids:
            closest = min(pool, key=lambda cid: abs(voter_ideo[vid] - voter_ideo[cid]))
            tally[closest] += 1

        elected = sorted(pool, key=lambda cid: -tally[cid])[:assembly_size]
        return set(elected)

    def _pure_asm(rng: _random.Random) -> set[Any]:
        return set(rng.sample(all_ids, min(assembly_size, num_voters)))

    def _stratified_asm(rng: _random.Random) -> set[Any]:
        age_targets = [max(1, round(p * assembly_size)) for p in age_dist]
        while sum(age_targets) > assembly_size:
            age_targets[age_targets.index(max(age_targets))] -= 1
        while sum(age_targets) < assembly_size:
            age_targets[age_targets.index(min(age_targets))] += 1

        result: list[int] = []
        for ag in range(len(age_dist)):
            n_ag = age_targets[ag]
            pool_ag = [vid for vid in all_ids if voter_age[vid] == ag]
            if not pool_ag:
                continue

            if edu_quota:
                n_low  = max(1, round(0.40 * n_ag))
                n_high = n_ag - n_low
                pool_low  = [vid for vid in pool_ag if voter_edu[vid] == 0]
                pool_high = [vid for vid in pool_ag if voter_edu[vid] == 1]
                result.extend(rng.sample(pool_low,  min(n_low,  len(pool_low))))
                result.extend(rng.sample(pool_high, min(n_high, len(pool_high))))
            else:
                result.extend(rng.sample(pool_ag, min(n_ag, len(pool_ag))))

        # Fill gap
        remaining = [vid for vid in all_ids if vid not in set(result)]
        while len(result) < assembly_size and remaining:
            pick = rng.choice(remaining)
            result.append(pick)
            remaining.remove(pick)
        return set(result[:assembly_size])

    # ── Main assembly run ─────────────────────────────────────────────────
    main_rng = _random.Random(seed + 100)
    elected_ids    = _elected_asm(_random.Random(seed))
    pure_ids       = _pure_asm(main_rng)
    stratified_ids = _stratified_asm(_random.Random(seed + 200))

    assemblies = {
        "elected":             _asm_metrics(elected_ids),
        "sortition_pure":      _asm_metrics(pure_ids),
        "sortition_stratified": _asm_metrics(stratified_ids),
    }

    # ── Winner by assembly ────────────────────────────────────────────────
    def _asm_winner(asm: set[Any]) -> Optional[str]:
        rnk = [
            sorted(sincere_utilities[vid].keys(), key=lambda k: -sincere_utilities[vid][k])
            for vid in asm
        ]
        return get_plurality_winner(rnk) if rnk else cand_names[0]

    winner_by_method = {
        "elected":             _asm_winner(elected_ids),
        "sortition_pure":      _asm_winner(pure_ids),
        "sortition_stratified": _asm_winner(stratified_ids),
    }
    consensus_possible = len(set(winner_by_method.values())) == 1

    # ── Monte Carlo variance ──────────────────────────────────────────────
    mc_elected:    list[float] = []
    mc_pure:       list[float] = []
    mc_stratified: list[float] = []

    for sim_i in range(num_sims):
        r = _random.Random(seed + 1000 + sim_i)
        def _mean_ideo(asm: set[Any]) -> float:
            return sum(voter_ideo[vid] for vid in asm) / len(asm) if asm else 0.0
        mc_elected.append(_mean_ideo(_elected_asm(r)))
        mc_pure.append(_mean_ideo(_pure_asm(_random.Random(seed + 2000 + sim_i))))
        mc_stratified.append(_mean_ideo(_stratified_asm(_random.Random(seed + 3000 + sim_i))))

    def _var(xs: list[float]) -> float:
        if len(xs) < 2:
            return 0.0
        return round(float(_np.var(xs)), 6)

    variance = {
        "elected":              _var(mc_elected),
        "sortition_pure":       _var(mc_pure),
        "sortition_stratified": _var(mc_stratified),
    }

    # ── Pedagogical note ──────────────────────────────────────────────────
    rep_elected = assemblies["elected"]["representativity"]
    rep_pure    = assemblies["sortition_pure"]["representativity"]
    note = (
        f"Avec {assembly_size} sièges et profil candidats "
        f"{'réaliste' if realistic_cands else 'neutre'}, "
        f"l'assemblée élue a une représentativité de {rep_elected:.2f} "
        f"contre {rep_pure:.2f} pour le tirage au sort pur. "
        f"{'Consensus atteint' if consensus_possible else 'Pas de consensus'} "
        f"entre les 3 modes de sélection."
    )

    return {
        "population": {
            "mean_ideology": full_mean_ideo,
            "gini_ideology": round(float(_np.std([voter_ideo[vid] for vid in all_ids])), 4),
            "demographics":  {
                "mean_age_group":       round(sum(voter_age.values()) / num_voters, 4),
                "mean_education_level": round(sum(voter_edu.values()) / num_voters, 4),
            },
        },
        "assemblies":         assemblies,
        "variance":           variance,
        "winner_by_method":   winner_by_method,
        "consensus_possible": consensus_possible,
        "pedagogical_note":   note,
    }, 200


# ── Party Dynamics ────────────────────────────────────────────────────────────

def _party_dynamics_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /party-dynamics — extracted for FastAPI v2.

    Simulate multi-election party system evolution (Duverger's Law).
    """

    num_voters    = max(100, min(1000, int(data.get("num_voters",        500))))
    ideology      = str(data.get("ideology",                "random"))
    seed          = int(data.get("seed",                     42))
    num_elections = max(1,  min(30,  int(data.get("num_elections",       10))))
    method        = str(data.get("method",                  "plurality"))
    surv_thr      = max(0.01, min(0.20, float(data.get("survival_threshold",   0.05))))
    emerge_prob   = max(0.00, min(1.00, float(data.get("emergence_probability", 0.10))))
    hotelling_a   = max(0.00, min(1.00, float(data.get("hotelling_adaptation",  0.10))))
    tactical_on   = bool(data.get("tactical_voting", True))
    # Pydantic Optional may pass null — fall back to the server default.
    initial_pts   = (data.get("initial_parties") or [
        {"name": "A", "x": -0.8, "y":  0.0, "support_pct": 0.10},
        {"name": "B", "x": -0.3, "y":  0.0, "support_pct": 0.25},
        {"name": "C", "x":  0.1, "y":  0.0, "support_pct": 0.30},
        {"name": "D", "x":  0.5, "y":  0.0, "support_pct": 0.25},
        {"name": "E", "x":  0.9, "y":  0.0, "support_pct": 0.10},
    ])[:10]

    if len(initial_pts) < 2:
        return {"error": "At least 2 initial parties required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)

    # ── Voter ideology (fixed across all elections) ───────────────────────
    if ideology == "polarized":
        h = num_voters // 2
        voter_x = _np.clip(
            _np.concatenate([_np.random.normal(-0.6, 0.2, h),
                             _np.random.normal( 0.6, 0.2, num_voters - h)]),
            -1.0, 1.0,
        )
    elif ideology == "normal":
        voter_x = _np.clip(_np.random.normal(0, 0.3, num_voters), -1.0, 1.0)
    else:
        voter_x = _np.random.uniform(-1.0, 1.0, num_voters)

    voter_median = float(_np.median(voter_x))

    # ── Active parties (mutable state) ───────────────────────────────────
    active: list[Dict[str, Any]] = [
        {
            "name":        str(p.get("name", f"P{i}")),
            "x":           max(-1.0, min(1.0, float(p.get("x", 0.0)))),
            "y":           max(-1.0, min(1.0, float(p.get("y", 0.0)))),
            "poll":        max(0.0,  float(p.get("support_pct", 1 / len(initial_pts)))),
        }
        for i, p in enumerate(initial_pts)
    ]
    # Normalize polls
    poll_total = sum(p["poll"] for p in active) or 1.0
    for p in active:
        p["poll"] /= poll_total

    initial_positions: Dict[str, float] = {p["name"]: p["x"] for p in active}
    party_counter      = len(active)
    rng                = _random.Random(seed + 1)
    all_elections: list[Dict[str, Any]] = []
    n_eff_curve: list[float] = []
    tactical_methods = {"plurality", "two_round", "irv"}

    # ── Vote-share helper ─────────────────────────────────────────────────
    def _vote_shares(parties: list[Any], polls: Dict[str, float]) -> Dict[str, float]:
        pxs = _np.array([p["x"] for p in parties])
        dists = _np.abs(voter_x[:, None] - pxs[None, :])   # (N, K)
        nearest = _np.argmin(dists, axis=1)

        apply_tac = tactical_on and method in tactical_methods
        if apply_tac:
            viable = _np.array([polls.get(p["name"], 0) >= 2 * surv_thr
                                 for p in parties])
            if viable.any() and not viable.all():
                masked = dists.copy()
                masked[:, ~viable] = 1e9
                tac_nearest = _np.argmin(masked, axis=1)
                mask = ~viable[nearest]
                nearest[mask] = tac_nearest[mask]

        counts = _np.bincount(nearest, minlength=len(parties))
        return {p["name"]: float(counts[i] / num_voters) for i, p in enumerate(parties)}

    # ── Gap finder for party emergence ────────────────────────────────────
    def _find_gap(pxs: list[Any]) -> float:
        cands = _np.linspace(-1.0, 1.0, 60)
        best_x, best_gap = 0.0, 0.0
        for cx in cands:
            g = min(abs(float(cx) - px) for px in pxs)
            if g > best_gap:
                best_gap, best_x = g, float(cx)
        return round(best_x, 2)

    # ── N_eff ─────────────────────────────────────────────────────────────
    def _n_eff(shares: Dict[str, float]) -> float:
        s = sum(v ** 2 for v in shares.values() if v > 0)
        return round(1.0 / s, 4) if s > 0 else 1.0

    # ── Simulation loop ───────────────────────────────────────────────────
    for k in range(num_elections):
        polls_dict = {p["name"]: p["poll"] for p in active}
        shares     = _vote_shares(active, polls_dict)
        n_eff      = _n_eff(shares)
        n_eff_curve.append(n_eff)

        winner = max(shares, key=shares.__getitem__) if shares else ""

        parties_snap = [
            {
                "name":     p["name"],
                "x":        round(p["x"], 4),
                "y":        round(p["y"], 4),
                "vote_pct": round(shares.get(p["name"], 0) * 100, 2),
                "seats":    round(shares.get(p["name"], 0) * 100),
                "survived": shares.get(p["name"], 0) >= surv_thr,
            }
            for p in active
        ]

        # Record before elimination
        all_elections.append({
            "election_n":        k + 1,
            "active_parties":    len(active),
            "parties":           parties_snap,
            "effective_parties": n_eff,
            "winner":            winner,
            "new_entrants":      [],   # filled in next iteration
            "eliminated":        [],   # filled below
        })

        # Eliminate
        eliminated = [p["name"] for p in active
                      if shares.get(p["name"], 0) < surv_thr]
        all_elections[-1]["eliminated"] = eliminated
        active = [p for p in active if shares.get(p["name"], 0) >= surv_thr]

        # Update polls
        for p in active:
            p["poll"] = shares.get(p["name"], 0)

        if not active:
            break

        # Hotelling adaptation
        for p in active:
            p["x"] = round(p["x"] + hotelling_a * (voter_median - p["x"]), 4)
            p["y"] = round(p["y"] + hotelling_a * (0.0 - p["y"]), 4)

        # Party emergence
        new_entrants: list[str] = []
        if emerge_prob > 0 and rng.random() < emerge_prob:
            gap_x = _find_gap([p["x"] for p in active])
            party_counter += 1
            new_name = f"Nouveau-{party_counter}"
            new_party: Dict[str, Any] = {
                "name": new_name, "x": gap_x, "y": 0.0, "poll": surv_thr * 1.5,
            }
            active.append(new_party)
            new_entrants.append(new_name)
            initial_positions[new_name] = gap_x

        if k + 1 < len(all_elections):
            all_elections[k + 1]["new_entrants"] = new_entrants
        else:
            # Mark on the NEXT election (we just finished election k)
            pass
        if new_entrants and k < num_elections - 1:
            all_elections[-1]["new_entrants"] = new_entrants

    # ── Summary ───────────────────────────────────────────────────────────
    n_eff_final = n_eff_curve[-1] if n_eff_curve else 1.0
    if n_eff_final < 2.5:
        final_system = "bipartite"
    elif n_eff_final < 4.0:
        final_system = "tripartite"
    else:
        final_system = "fragmented"

    duverger_confirmed = (method in ("plurality", "two_round")) and (n_eff_final < 2.5)

    convergence_speed: Optional[int] = None
    for i, nef in enumerate(n_eff_curve):
        if nef < 2.5:
            convergence_speed = i + 1
            break

    final_positions: Dict[str, float] = {p["name"]: p["x"] for p in active}
    ideology_drift = [
        {
            "party":     name,
            "initial_x": round(initial_positions[name], 4),
            "final_x":   round(final_positions.get(name, initial_positions[name]), 4),
        }
        for name in initial_positions
    ]

    note = (
        f"Avec la méthode '{method}' et {num_elections} élections, "
        f"le système passe de {len(initial_pts)} à {len(active)} partis. "
        f"Indice de Laakso-Taagepera final : {n_eff_final:.2f} "
        f"({'bipartisme' if final_system == 'bipartite' else 'multipartisme'}). "
        f"{'Loi de Duverger confirmée.' if duverger_confirmed else ''}"
    )

    return {
        "elections":               all_elections,
        "final_system":            final_system,
        "effective_parties_curve": n_eff_curve,
        "duverger_confirmed":      duverger_confirmed,
        "convergence_speed":       convergence_speed,
        "ideology_drift":          ideology_drift,
        "pedagogical_note":        note,
    }, 200


# ── Deliberation + Vote ───────────────────────────────────────────────────────

def _deliberation_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /deliberation — extracted for FastAPI v2 reuse.

    Simulate DeGroot-style deliberation before the vote.
    """
    import copy as _cpd

    num_voters     = max(50, min(500, int(data.get("num_voters",          200))))
    ideology       = str(data.get("ideology",               "random"))
    seed           = int(data.get("seed",                    42))
    delib_rounds   = max(1,  min(10,  int(data.get("deliberation_rounds",  5))))
    influence      = max(0.0, min(1.0, float(data.get("influence_weight",  0.3))))
    network_type   = str(data.get("network_type",           "random"))
    group_size     = max(3,  min(20,  int(data.get("group_size",           5))))
    arg_quality    = max(0.0, min(1.0, float(data.get("argument_quality",  0.5))))
    str(data.get("method",                 "plurality"))
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

    # ── Initial ideology (1D economy axis) ───────────────────────────────
    initial_ideo: _np.ndarray = _np.array([
        2.0 * v["issue_positions"].get("economy", 0.5) - 1.0
        for v in voters
    ])
    pop_median_init = float(_np.median(initial_ideo))

    # ── Helper functions ─────────────────────────────────────────────────
    def _win(utils: Dict[Any, Dict[str, float]]) -> Optional[str]:
        rnk = [sorted(utils[v["id"]], key=lambda k: -utils[v["id"]][k]) for v in voters]
        return get_plurality_winner(rnk) if rnk else cand_names[0]

    def _shares(utils: Dict[Any, Dict[str, float]]) -> Dict[str, float]:
        rnk = [sorted(utils[v["id"]], key=lambda k: -utils[v["id"]][k]) for v in voters]
        tally: Counter[Any] = Counter(r[0] for r in rnk if r)
        total = len(voters)
        return {c: round(tally.get(c, 0) / total, 4) for c in cand_names}

    def _regret(utils: Dict[Any, Dict[str, float]], winner: Optional[str]) -> float:
        if winner is None:
            return 0.0
        return round(
            sum(max(utils[v["id"]].values()) - utils[v["id"]].get(winner, 0)
                for v in voters) / len(voters), 4
        )

    def _cw(utils: Dict[Any, Dict[str, float]]) -> Optional[str]:
        rnk = [sorted(utils[v["id"]], key=lambda k: -utils[v["id"]][k]) for v in voters]
        return get_condorcet_winner(rnk)

    def _recalc_utils(ideo: _np.ndarray) -> Dict[Any, Dict[str, float]]:
        """Recompute utilities after ideology shift (economy axis only)."""
        out: Dict[Any, Dict[str, float]] = {}
        for i_v, v in enumerate(voters):
            orig = v["issue_positions"]["economy"]
            v["issue_positions"]["economy"] = float(_np.clip((ideo[i_v] + 1) / 2, 0, 1))
            out[v["id"]] = {
                c["name"]: calculate_utility(v, c, issues)["utility"]
                for c in candidates
            }
            v["issue_positions"]["economy"] = orig
        return out

    def _form_groups(ideo: _np.ndarray, rng: _random.Random) -> list[Any]:
        n   = len(ideo)
        idx = list(range(n))
        if network_type == "complete":
            return [idx]
        if network_type == "echo_chamber":
            sorted_idx = sorted(idx, key=lambda i: ideo[i])
            return [sorted_idx[i:i + group_size] for i in range(0, n, group_size)]
        if network_type == "bridge":
            sorted_idx = sorted(idx, key=lambda i: ideo[i])
            half       = n // 2
            left, right = sorted_idx[:half], sorted_idx[half:]
            rng.shuffle(left); rng.shuffle(right)
            g2     = max(1, group_size // 2)
            groups = []
            for k in range(max(len(left), len(right)) // g2):
                g = left[k * g2:(k + 1) * g2] + right[k * g2:(k + 1) * g2]
                if g:
                    groups.append(g)
            return groups or [idx]
        # random
        rng.shuffle(idx)
        return [idx[i:i + group_size] for i in range(0, n, group_size)]

    # ── Pre-deliberation ─────────────────────────────────────────────────
    pre_win    = _win(sincere_utilities)
    pre_shares = _shares(sincere_utilities)
    pre_cw     = _cw(sincere_utilities)
    pre_regret = _regret(sincere_utilities, pre_win)
    pre_var    = float(_np.var(initial_ideo))

    # ── Deliberation rounds ───────────────────────────────────────────────
    current_ideo  = initial_ideo.copy()
    current_utils = _cpd.deepcopy(sincere_utilities)
    rng_d         = _random.Random(seed + 100)
    per_round: list[Dict[str, Any]] = []

    for round_k in range(delib_rounds):
        groups  = _form_groups(current_ideo, rng_d)
        new_ideo = current_ideo.copy()

        for group in groups:
            if len(group) < 2:
                continue
            g_arr = current_ideo[group]

            if network_type == "echo_chamber":
                # Amplification: push group toward its own extreme
                g_mean  = float(g_arr.mean())
                g_std   = max(0.02, float(g_arr.std()))
                sign    = 1.0 if g_mean >= 0 else -1.0
                target  = float(_np.clip(g_mean + sign * g_std * 0.4, -1.0, 1.0))
            else:
                # Quality-weighted mean: high quality → bias toward median
                weights = _np.ones(len(group))
                if arg_quality > 0:
                    for ki, j in enumerate(group):
                        prox = max(0.0, 1.0 - abs(float(current_ideo[j]) - pop_median_init))
                        weights[ki] = (1.0 - arg_quality) + arg_quality * prox
                weights /= max(float(weights.sum()), 1e-9)
                target = float(_np.clip(_np.dot(weights, g_arr), -1.0, 1.0))

            for i in group:
                new_ideo[i] = float(_np.clip(
                    current_ideo[i] + influence * (target - current_ideo[i]),
                    -1.0, 1.0,
                ))

        current_ideo  = new_ideo
        current_utils = _recalc_utils(current_ideo)

        rnd_winner = _win(current_utils)
        per_round.append({
            "round":              round_k + 1,
            "variance":           round(float(_np.var(current_ideo)), 4),
            "mean_position":      round(float(_np.mean(current_ideo)), 4),
            "winner_if_voted_now": rnd_winner,
        })

    # ── Post-deliberation ─────────────────────────────────────────────────
    post_win    = _win(current_utils)
    post_shares = _shares(current_utils)
    post_cw     = _cw(current_utils)
    post_regret = _regret(current_utils, post_win)
    post_var    = float(_np.var(current_ideo))

    winner_changed    = pre_win != post_win
    opinion_shift     = round(float(_np.mean(_np.abs(current_ideo - initial_ideo))), 4)
    convergence_rate  = round(max(0.0, 1.0 - post_var / pre_var), 4) if pre_var > 1e-9 else 0.0
    polarization_chg  = round(post_var - pre_var, 4)
    regret_improv     = round((pre_regret - post_regret) / pre_regret * 100, 2) if pre_regret > 1e-9 else 0.0

    _NET_DESC: Dict[str, str] = {
        "echo_chamber": "Les chambres d'écho amplifient les clivages — les groupes homogènes se radicalisent.",
        "bridge":       "Les ponts entre les camps permettent une convergence progressive des opinions.",
        "complete":     "En réseau complet, la délibération converge rapidement vers le consensus de masse.",
        "random":       "Le réseau aléatoire produit une convergence modérée sans dynamique extrême.",
    }
    network_effect = _NET_DESC.get(network_type, "")

    poldir  = "augmente" if polarization_chg > 0 else "diminue"
    regdir  = "améliore" if regret_improv > 0 else "dégrade"
    note = (
        f"En réseau '{network_type}', {delib_rounds} rounds de délibération "
        f"{'changent' if winner_changed else 'ne changent pas'} le vainqueur. "
        f"La polarisation {poldir} de {abs(round(polarization_chg * 100, 1))}%. "
        f"Le regret bayésien se {regdir} de {abs(regret_improv):.1f}%."
    )

    return {
        "pre_deliberation": {
            "winner":            pre_win,
            "vote_shares":       pre_shares,
            "condorcet_winner":  pre_cw,
            "mean_regret":       pre_regret,
            "ideology_variance": round(pre_var, 4),
        },
        "post_deliberation": {
            "winner":            post_win,
            "vote_shares":       post_shares,
            "condorcet_winner":  post_cw,
            "mean_regret":       post_regret,
            "ideology_variance": round(post_var, 4),
        },
        "winner_changed":       winner_changed,
        "deliberation_effect": {
            "opinion_shift_mean": opinion_shift,
            "convergence_rate":   convergence_rate,
            "polarization_change": polarization_chg,
            "regret_improvement": regret_improv,
        },
        "per_round":      per_round,
        "network_effect": network_effect,
        "pedagogical_note": note,
    }, 200


# ── /api/election/power-indices ───────────────────────────────────────────────

# Shapley-Shubik enumerates every arrival order: 10! is 3.6M permutations, and
# each extra party multiplies that again. Past this the index is reported as 0
# rather than hanging the request.
_SHAPLEY_MAX_PARTIES = 10

_CoalitionTest = Callable[[frozenset[Any]], bool]


def _pi_forbidden_pairs(
    names: List[str],
    pariah_set: set[Any],
    constraints_raw: List[Dict[str, str]],
) -> set[Any]:
    """Pairs that may never sit in the same coalition: the explicit constraints,
    plus a pariah's pair with every other party (the cordon sanitaire)."""
    forbidden: set[Any] = set()
    for c in constraints_raw:
        a, b = c.get("party_a", ""), c.get("party_b", "")
        if a in names and b in names:
            forbidden.add(frozenset([a, b]))
    for par in pariah_set:
        for other in names:
            if other != par:
                forbidden.add(frozenset([par, other]))
    return forbidden


def _pi_pivot(
    perm: tuple[str, ...],
    seats_map: Dict[str, int],
    majority_threshold: int,
    is_valid: _CoalitionTest,
) -> Optional[str]:
    """The party whose arrival first carries this ordering over the majority
    line, or None if the ordering never reaches one."""
    running: frozenset[Any] = frozenset()
    for party in perm:
        running = running | {party}
        if is_valid(running) and sum(seats_map[m] for m in running) >= majority_threshold:
            return party
    return None


def _pi_shapley(
    names: List[str],
    seats_map: Dict[str, int],
    majority_threshold: int,
    is_valid: _CoalitionTest,
) -> tuple[Dict[str, float], Dict[str, int]]:
    """Shapley-Shubik: over every arrival order, count how often each party is
    the pivot. Returns the normalised index and the raw pivot counts."""
    pivot_counts: Dict[str, int] = {name: 0 for name in names}
    if len(names) > _SHAPLEY_MAX_PARTIES:
        return {name: 0.0 for name in names}, pivot_counts

    total_perms = 0
    for perm in itertools.permutations(names):
        total_perms += 1
        pivot = _pi_pivot(perm, seats_map, majority_threshold, is_valid)
        if pivot is not None:
            pivot_counts[pivot] += 1

    shapley = {
        name: round(pivot_counts[name] / total_perms, 6) if total_perms else 0.0
        for name in names
    }
    return shapley, pivot_counts


def _pi_critical_members(coalition: frozenset[Any], wins: _CoalitionTest) -> List[Any]:
    """The members whose departure would cost this coalition its majority."""
    return [m for m in coalition if not wins(coalition - {m})]


def _pi_banzhaf(
    names: List[str],
    seats_map: Dict[str, int],
    wins: _CoalitionTest,
) -> tuple[Dict[str, float], Dict[str, int], List[Dict[str, Any]]]:
    """Banzhaf: over every winning coalition, count how often each member is
    critical. Also collects the winning coalitions themselves — one is minimal
    exactly when every one of its members is critical."""
    critical_counts: Dict[str, int] = {name: 0 for name in names}
    viable: List[Dict[str, Any]] = []

    for r in range(1, len(names) + 1):
        for combo in itertools.combinations(names, r):
            coalition = frozenset(combo)
            if not wins(coalition):
                continue
            critical = _pi_critical_members(coalition, wins)
            for member in critical:
                critical_counts[member] += 1
            viable.append({
                "parties": sorted(combo),
                "seats":   sum(seats_map[m] for m in combo),
                "minimal": len(critical) == len(combo),
            })

    total_critical = sum(critical_counts.values())
    banzhaf = {
        name: round(critical_counts[name] / total_critical, 6) if total_critical else 0.0
        for name in names
    }
    return banzhaf, critical_counts, viable


def _pi_party_results(
    parties: List[Dict[str, Any]],
    total_seats: int,
    shapley: Dict[str, float],
    banzhaf: Dict[str, float],
    critical_counts: Dict[str, int],
    pivot_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Per-party row. `power_ratio` is the point of the whole endpoint: coalition
    power divided by seat share, so 1.0 means a party is exactly as powerful as
    it is large."""
    results = []
    for p in parties:
        name = p["name"]
        seat_pct = p["seats"] / total_seats if total_seats > 0 else 0.0
        sh = shapley.get(name, 0.0)
        results.append({
            "name":           name,
            "seats":          p["seats"],
            "seat_pct":       round(seat_pct, 4),
            "shapley_index":  sh,
            "banzhaf_index":  banzhaf.get(name, 0.0),
            "power_ratio":    round(sh / seat_pct, 4) if seat_pct > 0 else 0.0,
            "critical_count": critical_counts.get(name, 0),
            "pivot_count":    pivot_counts.get(name, 0),
            "is_pariah":      p["pariah"],
        })
    return results


def _pi_surprises(party_results: List[Dict[str, Any]]) -> List[str]:
    """The cases where seat count and real power come apart."""
    surprises: List[str] = []
    for pr in party_results:
        ratio = pr["power_ratio"]
        if ratio > 1.5:
            surprises.append(
                f"{pr['name']} : {pr['seats']} sièges ({round(pr['seat_pct']*100)}%) "
                f"mais Shapley={round(pr['shapley_index']*100, 1)}% — "
                f"sur-puissant (×{ratio:.2f})"
            )
        elif ratio < 0.5 and pr["seats"] > 0 and not pr["is_pariah"]:
            surprises.append(
                f"{pr['name']} : {pr['seats']} sièges mais Shapley={round(pr['shapley_index']*100, 1)}% "
                f"— sous-puissant (ratio={ratio:.2f})"
            )
        elif pr["is_pariah"] and pr["seats"] > 0:
            surprises.append(
                f"{pr['name']} : {pr['seats']} sièges mais pouvoir=0 (paria, exclu de toutes les coalitions)"
            )
    return surprises


def _pi_note(party_results: List[Dict[str, Any]]) -> str:
    if not party_results:
        return "Aucun parti fourni."

    top = max(party_results, key=lambda x: x["shapley_index"])
    note = (
        f"Shapley-Shubik 1954 : le parti '{top['name']}' détient "
        f"{round(top['shapley_index']*100, 1)}% du pouvoir de coalition "
        f"pour {round(top['seat_pct']*100, 1)}% des sièges. "
    )
    parias_with_seats = [p for p in party_results if p["is_pariah"] and p["seats"] > 0]
    if parias_with_seats:
        names_str = ", ".join(p["name"] for p in parias_with_seats)
        total_paria_seats = sum(p["seats"] for p in parias_with_seats)
        note += (
            f"Les partis '{names_str}' totalisent {total_paria_seats} sièges "
            f"mais ont un pouvoir réel de 0 (cordon sanitaire). "
        )
    return note + (
        "Banzhaf (1965) : un parti est critique si son départ fait "
        "passer la coalition de gagnante à perdante."
    )


def _pi_normalise(
    raw_parties: List[Dict[str, Any]],
    majority_threshold: int,
) -> tuple[List[Dict[str, Any]], List[str], Dict[str, int], int, int]:
    """Clamp the request into the shapes the indices need. A threshold of 0 or
    less means "unspecified": fall back to a simple majority of the seats."""
    parties: List[Dict[str, Any]] = [
        {
            "name":   str(p.get("name", "?")),
            "seats":  max(0, int(p.get("seats", 0))),
            "pariah": bool(p.get("pariah", False)),
        }
        for p in raw_parties
    ]
    total_seats = sum(p["seats"] for p in parties)
    if majority_threshold <= 0:
        majority_threshold = total_seats // 2 + 1
    names = [p["name"] for p in parties]
    seats_map = {p["name"]: p["seats"] for p in parties}
    return parties, names, seats_map, total_seats, majority_threshold


def _pi_zeros(names: List[str]) -> tuple[Dict[str, float], Dict[str, int]]:
    """Neutral indices, for an index the caller switched off."""
    return {n: 0.0 for n in names}, {n: 0 for n in names}


def _power_indices_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /power-indices — extracted for FastAPI v2."""
    raw_parties: List[Dict[str, Any]] = data.get("parties") or []
    if not raw_parties:
        return {"error": "parties required"}, 400

    parties, names, seats_map, total_seats, majority_threshold = _pi_normalise(
        raw_parties, int(data.get("majority_threshold", 0)),
    )
    forbidden = _pi_forbidden_pairs(
        names,
        {p["name"] for p in parties if p["pariah"]},
        data.get("coalition_constraints") or [],
    )

    def is_valid(members: frozenset[Any]) -> bool:
        """True when no forbidden pair sits entirely inside members."""
        return not any(pair <= members for pair in forbidden)

    def wins(members: frozenset[Any]) -> bool:
        return is_valid(members) and sum(seats_map[m] for m in members) >= majority_threshold

    zero_float, zero_int = _pi_zeros(names)
    shapley, pivot_counts = (
        _pi_shapley(names, seats_map, majority_threshold, is_valid)
        if data.get("calculate_shapley", True)
        else (zero_float, zero_int)
    )
    banzhaf, critical_counts, viable_coalitions = (
        _pi_banzhaf(names, seats_map, wins)
        if data.get("calculate_banzhaf", True)
        else (zero_float, zero_int, [])
    )

    party_results = _pi_party_results(
        parties, total_seats, shapley, banzhaf, critical_counts, pivot_counts,
    )

    return {
        "total_seats":        total_seats,
        "majority_threshold": majority_threshold,
        "parties":            party_results,
        "viable_coalitions":  viable_coalitions[:50],
        "power_surprises":    _pi_surprises(party_results),
        "pedagogical_note":   _pi_note(party_results),
    }, 200

