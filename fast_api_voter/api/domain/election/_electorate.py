"""
api.domain.election._electorate — shared electorate-construction helpers,
extracted from the workers.py monolith so worker clusters can be split into
their own modules without importing back into workers.py (no cycles).

Pure builders: spec -> (candidates, voters, true utilities, names), the
method-comparison wrapper, and a lightweight winners-only snapshot.
"""
from __future__ import annotations

import random
from typing import Any, Dict

import numpy as np

from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.simulation_voting_utils import calculate_utility, create_voter
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.blank_vote_rules import BlankVoteRule, apply_blank_rule
from api.engine.utils.blank_contagion import simulate_blank_contagion
from api.engine.utils.demographic_data import _seeded_rng_pair
from ._helpers import (
    build_candidate_from_xy as _build_candidate_from_xy,
    inter_method_agreement as _inter_method_agreement,
)


def _build_base_electorate(
    cand_specs: list[dict[str, Any]],
    num_voters: int,
    ideology: str,
    seed: int,
    issues: list[str],
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], Dict[Any, Dict[str, float]], list[str]]:
    """
    Build candidates, voters, and true utilities from spec.
    Returns (candidates, voters, true_utilities, cand_names).

    Seeds a local RNG pair from *seed* rather than reseeding the shared
    random/np.random module-level singletons: this function used to rely on
    the caller reseeding those globals immediately beforehand, which meant
    "same seed -> same result" only held if nothing else in the process
    touched random/np.random between the reseed and this call — false under
    any concurrent access (see election_service.py for the full writeup).
    """
    import copy  # noqa: F401 — kept for symmetry, not actually needed here

    rng, np_rng = _seeded_rng_pair(seed)

    cand_names = [str(s.get("name", f"C{i}")) for i, s in enumerate(cand_specs)]

    candidates = [
        _build_candidate_from_xy(
            i,
            cand_names[i],
            max(-1.0, min(1.0, float(s.get("x", 0.0)))),
            max(-1.0, min(1.0, float(s.get("y", 0.0)))),
            issues,
        )
        for i, s in enumerate(cand_specs)
    ]

    voters = [
        create_voter(issues, i, ideology_distribution=ideology, rng=rng, np_rng=np_rng)
        for i in range(num_voters)
    ]

    true_utilities: Dict[Any, Dict[str, float]] = {
        v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"] for c in candidates}
        for v in voters
    }

    return candidates, voters, true_utilities, cand_names


def _reseed_and_build_electorate(
    cand_specs: list[dict[str, Any]],
    num_voters: int,
    ideology: str,
    seed: int,
) -> tuple[
    list[Dict[str, Any]], list[Dict[str, Any]], Dict[Any, Dict[str, float]], list[str], list[str]
]:
    """Reseed the shared `random`/`numpy.random` singletons from *seed*, then
    build the electorate via `_build_base_electorate`.

    This is the *legacy* reseed pattern used by several older `workers_*.py`
    workers (`workers_advanced.py`, `workers_behavioral.py`,
    `workers_dynamics.py`, `workers_mechanisms.py`) — predating the local
    seeded-RNG-pair fix documented on `_build_base_electorate`/
    `election_service.py` for the concurrency issue with reseeding shared
    singletons. Kept exactly as-is here: this is a pure duplication
    extraction (the same 4-line block was copy-pasted across 13 call sites,
    jscpd-flagged, CODE_AUDIT.md §4/§7), not a behaviour change — do not use
    this as a template for new workers, prefer `_build_base_electorate`
    directly with `_seeded_rng_pair`.

    Returns (candidates, voters, true_utilities, cand_names, issues) so
    every call site keeps `issues` in scope afterwards exactly as before
    (it is always `DEFAULT_ISSUES`, echoed back rather than re-imported at
    each site).
    """
    random.seed(seed)
    np.random.seed(seed)
    issues = DEFAULT_ISSUES
    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    return candidates, voters, true_utilities, cand_names, issues


def _apply_blank_contagion(
    voters: list[Dict[str, Any]],
    contagion_cfg: Dict[str, Any],
    num_voters: int,
    seed: int,
) -> Dict[str, Any]:
    """Run the SIS blank-vote contagion model and reduce each voter's
    `blank_threshold` in place by 0.4x the resulting final blank rate.

    Extracted from the identical block duplicated across
    `election_service.py` and 4 workers in `workers.py`
    (`_divergence_worker`, `_campaign_sensitivity_worker`,
    `_combined_effects_worker`, `_simulate_pipeline_worker` — jscpd-flagged,
    CODE_AUDIT.md §4/§7). Callers keep their own on/off condition
    (`contagion_on`, sometimes `and blank_enabled`) and their own choice of
    which voters list to mutate (the live electorate, or a `copy.deepcopy`
    of it) — only the identical inner computation moved here.

    Returns `{"final_blank_rate", "beta", "gamma"}` for the one call site
    (`_simulate_pipeline_worker`) that reports these back in its own
    response; other callers can ignore the return value.
    """
    beta    = max(0.0, min(1.0, float(contagion_cfg.get("beta",  0.15))))
    gamma   = max(0.0, min(1.0, float(contagion_cfg.get("gamma", 0.10))))
    net_map = {"random": "random", "watts_strogatz": "small-world", "block": "clustered"}
    net     = net_map.get(str(contagion_cfg.get("network", "random")), "random")

    contagion_result = simulate_blank_contagion(
        num_voters=num_voters,
        initial_blank_rate=0.05,
        contagion_rate=beta,
        recovery_rate=gamma,
        num_rounds=10,
        network_type=net,
        seed=seed,
    )
    final_blank_rate = contagion_result.get("final_blank_rate", 0.05)
    reduction = final_blank_rate * 0.4
    for v in voters:
        v["blank_threshold"] = max(0.05, v["blank_threshold"] - reduction)

    return {"final_blank_rate": final_blank_rate, "beta": beta, "gamma": gamma}


def _run_methods_on_electorate(
    voters: list[Dict[str, Any]],
    candidates: list[Dict[str, Any]],
    utilities: Dict[Any, Dict[str, float]],
    issues: list[str],
    blank_enabled: bool,
    blank_rule: BlankVoteRule,
) -> Dict[str, Any]:
    """
    Run compare_all_methods and optionally apply blank-vote rule.
    Returns structured dict: { method_name: { winner, winner_after_rule, ... } }.
    """
    result        = compare_all_methods(
        voters, candidates, issues,
        blank_vote=blank_enabled,
        override_utilities=utilities,
    )
    condorcet_winner = result.get("condorcet_winner")
    blank_pct        = result.get("blank_pct") or 0.0
    methods_data     = result.get("methods", {})

    methods_out: Dict[str, Any] = {}
    for method_name, md in methods_data.items():
        winner = md.get("winner")
        entry: Dict[str, Any] = {"winner": winner}
        if blank_enabled:
            rule_result = apply_blank_rule(winner=winner, blank_pct=blank_pct, rule=blank_rule)
            entry["winner_after_rule"] = rule_result.get("winner")
            entry["blank_triggered"]   = rule_result.get("blank_triggered", False)
        methods_out[method_name] = entry

    return {
        "methods":               methods_out,
        "inter_method_agreement": _inter_method_agreement(methods_out),
        "condorcet_winner":      condorcet_winner,
        "blank_rate":            round(blank_pct, 4),
    }


def _snapshot_election_winners(
    voters:     list[Dict[str, Any]],
    candidates: list[Dict[str, Any]],
    utilities:  Dict[Any, Dict[str, float]],
    issues:     list[str],
    blank_enabled: bool,
    blank_rule: BlankVoteRule,
) -> Dict[str, Dict[str, Any]]:
    """Winner + vote share per method for one snapshot (a campaign day, a
    factor combination).

    This was a hand-rolled registry justified as "lighter than
    compare_all_methods() -- skips strategic_vulnerability". That metric is off
    by default now, so the engine IS the lighter path -- and it answers all 34
    rules where the copy answered 14, silently omitting 20 (kemeny_young,
    copeland, ranked_pairs, majority_judgment, nash, ...) for the same
    electorate /simulate reported in full. `inter_method_agreement`, built on
    top of this and labelled "toutes les methodes" in the UI, was therefore
    measured over 41% of them.

    `vote_share` is the engine's `majority_satisfaction`: the same formula the
    copy computed, under a different name.
    """
    report = compare_all_methods(
        voters, candidates, issues,
        blank_vote=blank_enabled,
        override_utilities=utilities,
        # Explicit, not inherited: the default flipped True -> False one commit
        # ago, and at these endpoints' own cap (6 candidates, 200 voters) the
        # True path measures 13 s per call -- 8 combos of /combined-effects would
        # be ~104 s against a 180 s worker timeout. Too load-bearing to leave to
        # a default in another module.
        compute_strategic=False,
    )
    blank_pct = report.get("blank_pct") or 0.0

    methods_out: Dict[str, Dict[str, Any]] = {}
    for method, md in report.get("methods", {}).items():
        winner = md.get("winner")
        entry: Dict[str, Any] = {
            "winner":     winner,
            # None when no winner; the copy reported 0.0, so keep that.
            "vote_share": md.get("majority_satisfaction") or 0.0,
        }
        if blank_enabled:
            rule_res = apply_blank_rule(
                winner=winner, blank_pct=blank_pct, rule=blank_rule
            )
            entry["winner_after_rule"] = rule_res.get("winner")
        methods_out[method] = entry

    return methods_out

