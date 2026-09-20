"""
election/_helpers.py — small generic helpers shared by election routes.

Extracted from the formerly-monolithic election.py to start carving the
package into reviewable chunks. Only the truly generic helpers (no route
state, no Flask context) live here. Workers (the per-route compute) stay
with their route file.

Future PRs will progressively move route groups into sibling modules
(perturbations.py, electoral_systems.py, dynamics.py, experimental.py).
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from api.engine.constants import ECONOMY_ISSUES, ENV_ISSUES, SOCIAL_ISSUES

# Used to assign a party label deterministically by candidate index.
PARTY_CYCLE: List[str] = ["Green", "Liberal", "Conservative", "Independent"]

# Standard candidate cap for single-winner endpoints. Raised from 6 to 8 so
# France 2002 (8 historical candidates) is processed without silent truncation.
# Every rule is exact across the whole 2..8 range: Kemeny-Young used to
# approximate above 6, which meant the 8-candidate case this cap exists for was
# the one getting a degraded answer — and a different one from the client, which
# brute-forced it exactly. Its exact path is now DP over candidate subsets and
# `_KY_EXACT_CAP` is 10 (simulation_ranked_utils).
SINGLE_WINNER_CAP: int = 8


def build_candidate_from_xy(
    i: int, name: str, x: float, y: float, issues: List[str]
) -> Dict[str, Any]:
    """Build a candidate dict from explicit 2D ideological position (x, y in [-1, 1])."""
    econ_pos = (x + 1) / 2
    soc_pos  = (y + 1) / 2
    env_pos  = 1.0 - econ_pos

    policies = {
        issue: (
            econ_pos if issue in ECONOMY_ISSUES else
            env_pos  if issue in ENV_ISSUES      else
            soc_pos  if issue in SOCIAL_ISSUES   else
            (econ_pos + soc_pos) / 2
        )
        for issue in issues
    }
    return {
        "id":               i,
        "name":             name,
        "party":            PARTY_CYCLE[i % len(PARTY_CYCLE)],
        "party_lean":       x,
        "ideology_position": econ_pos,
        "policies":         policies,
        "charisma":         0.7,
        "scandals":         0,
        "campaign_funds":   500_000,
        "experience":       10,
        "popularity":       0.6,
    }


def gini(values: List[float]) -> float:
    """Normalised Gini coefficient for a list of non-negative values ∈ [0,1]."""
    n = len(values)
    if n <= 1:
        return 0.0
    total = sum(values)
    if total == 0.0:
        return 0.0
    sv = sorted(values)
    cum = sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(sv))
    return round(cum / (n * total), 4)


def dhondt(vote_shares: Dict[str, float], total_seats: int) -> Dict[str, int]:
    """D'Hondt proportional seat allocation.

    vote_shares: {party_name: fraction_of_vote}  (values sum ≈ 1)
    Returns {party_name: seats_awarded}.
    """
    seats: Dict[str, int] = {p: 0 for p in vote_shares}
    for _ in range(total_seats):
        quotients = {p: vote_shares[p] / (seats[p] + 1) for p in vote_shares}
        winner = max(quotients, key=lambda k: quotients[k])
        seats[winner] += 1
    return seats


def tied_extremes(values: Mapping[str, float]) -> tuple[List[str], List[str]]:
    """Every key tied at the lowest value and every key tied at the highest, in
    insertion order; both empty when all values are equal, since then nothing
    stands out.

    For "best / worst method" read off a per-method score. Methods producing the
    same outcome score exactly the same, and those ties are the norm: the lowest
    Bayesian regret on /interpret is shared by 25-33 of 34 methods, the top jury
    accuracy by 4 or 5 of 5 methods on most /jury runs. `min(d, key=d.get)`
    returns whichever tied key comes first, so a single name was arbitrary.
    """
    lo, hi = min(values.values(), default=0), max(values.values(), default=0)
    if lo == hi:
        return [], []
    return (
        [k for k, v in values.items() if v == lo],
        [k for k, v in values.items() if v == hi],
    )


def modal_keys(counts: Mapping[str, int]) -> List[str]:
    """Every key tied for the highest count, sorted; empty only for an empty
    tally.

    For "who won the most trials / runs / simulations", where `tied_extremes` is
    the wrong tool: it collapses "all values equal" to empty, which is right for a
    per-method score (nothing stands out) but wrong for a winner distribution,
    where two candidates on 15 trials each are both leaders and the baseline being
    one of them is exactly what a caller needs to know. `Counter.most_common(1)`
    returned whichever candidate won the first trial, so a 15-15 split could
    contradict the baseline and report a robust scenario as fragile.
    """
    top = max(counts.values(), default=0)
    return sorted(k for k, v in counts.items() if v == top)


def result_label(winner: Optional[str]) -> str:
    """A winner for prose, or "égalité" when the rule elected nobody (an exact
    tie). `winner or cand_names[0]` used to report such a tie as a win for the
    first-listed candidate."""
    return f"'{winner}'" if winner else "égalité"


def prose_list(names: List[str], conj: str = "et", others: str = "autres", shown: int = 3) -> str:
    """'a, b et c' -- or 'a, b, c et 28 autres' past `shown` names, since a tie
    can span 30 methods. Pass conj="and", others="others" for English."""
    if len(names) <= shown:
        return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {conj} {names[-1]}"
    return f"{', '.join(names[:shown])} {conj} {len(names) - shown} {others}"


def inter_method_agreement(methods_data: Dict[str, Any]) -> float:
    """Fraction of voting methods that agree on the same winner (0..1)."""
    winners = [md.get("winner") for md in methods_data.values() if md.get("winner")]
    if not winners:
        return 0.0
    most_common = Counter(winners).most_common(1)[0][1]
    return round(most_common / len(winners), 4)


def parse_optional_election_configs(
    data: Dict[str, Any],
) -> tuple[bool, str, Dict[str, Any], bool, Dict[str, Any], bool, Dict[str, Any], bool, int, float]:
    """Parse the optional `blank_vote` (+ nested `contagion`),
    `information_model` and `campaign` sub-configs shared by the unified
    election pipeline, deriving their on/off flags and clamped numeric
    params.

    Extracted from the identical block duplicated between
    `election_service.py`'s `simulate` and
    `workers.py`'s `_simulate_pipeline_worker` (jscpd-flagged,
    CODE_AUDIT.md §4/§7). The candidate-count validation that immediately
    follows this block at both call sites stays there — it depends on each
    caller's own `cand_specs` (parsed with a different default/cap at each
    site), so it isn't part of this shared computation.

    Returns (blank_enabled, blank_rule_str, contagion_cfg, contagion_on,
    info_cfg, info_enabled, campaign_cfg, campaign_on, num_days,
    polling_effect).
    """
    blank_cfg      = data.get("blank_vote", {}) or {}
    blank_enabled  = bool(blank_cfg.get("enabled", False))
    blank_rule_str = str(blank_cfg.get("rule", "symbolic"))
    contagion_cfg  = blank_cfg.get("contagion", {}) or {}
    contagion_on   = bool(contagion_cfg.get("enabled", False))

    info_cfg     = data.get("information_model", {}) or {}
    info_enabled = bool(info_cfg.get("enabled", False))

    campaign_cfg   = data.get("campaign", {}) or {}
    campaign_on    = bool(campaign_cfg.get("enabled", False))
    num_days       = max(7, min(60, int(campaign_cfg.get("num_days",       30))))
    polling_effect = max(0.0, min(1.0, float(campaign_cfg.get("polling_effect", 0.3))))

    return (
        blank_enabled, blank_rule_str, contagion_cfg, contagion_on,
        info_cfg, info_enabled, campaign_cfg, campaign_on,
        num_days, polling_effect,
    )


def reject_unknown_methods(
    requested: Iterable[str], supported: Sequence[str],
) -> Optional[tuple[Dict[str, Any], int]]:
    """A 400 naming every unsupported method, or None. For the direct-call path:
    over HTTP each request schema's Literal already turns a bad name into a 422."""
    unknown = [m for m in requested if m not in supported]
    if not unknown:
        return None
    return {
        "error": f"unknown voting method(s) {', '.join(repr(m) for m in unknown)} -- "
                 f"supported: {', '.join(supported)}"
    }, 400
