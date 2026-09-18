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
from typing import Any, Dict, List, Optional

from api.engine.constants import ECONOMY_ISSUES, ENV_ISSUES, SOCIAL_ISSUES
from api.engine.utils.method_registry import SCORE_RULES, rule_winner
from api.engine.utils.simulation_score_utils import get_majority_judgment_winner

# Used to assign a party label deterministically by candidate index.
PARTY_CYCLE: List[str] = ["Green", "Liberal", "Conservative", "Independent"]

# Standard candidate cap for single-winner endpoints. Raised from 6 to 8 so
# France 2002 (8 historical candidates) is processed without silent truncation.
# Kemeny-Young falls back to KwikSort approximation beyond 6 (see
# simulation_ranked_utils.get_kemeny_young_winner — graceful degradation).
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
    `election_service.py`'s `ElectionService.simulate` and
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

# ── Winner from a utility matrix ──────────────────────────────────────────────
# Four dispatchers in workers_behavioral.py each rebuilt this: rankings from the
# utilities, 0-5 score ballots from the same, then an if-chain over method names
# ending in a silent `get_plurality_winner` fallback. The sincere-approval tally
# was written out three times. `winner_from_utilities` is that, once.

#: The rules a utility matrix can express. Ranked rules read the rankings it
#: induces; `approval` and `majority_judgment` read the utilities themselves,
#: which is why neither is a plain registry lookup.
UTILITY_METHODS: tuple[str, ...] = (
    "plurality", "borda", "irv", "schulze", "two_round",
    "approval", "majority_judgment", "star_voting",
)


def rankings_from_utilities(
    utilities: Dict[Any, Dict[str, float]], voters: List[Dict[str, Any]]
) -> List[List[str]]:
    """Each voter's candidates, their favourite first."""
    return [
        sorted(utilities[v["id"]].keys(), key=lambda n: -utilities[v["id"]][n])
        for v in voters
    ]


def sincere_approval_winner(
    utilities: Dict[Any, Dict[str, float]],
    voters: List[Dict[str, Any]],
    cand_names: List[str],
) -> str:
    """Approve everyone above your own mean utility, then count. A ranking
    cannot express where a voter's mean falls, so this reads the utilities."""
    tally: "Counter[Any]" = Counter()
    for v in voters:
        u = utilities[v["id"]]
        threshold = sum(u.values()) / len(u) if u else 0.5
        for name, value in u.items():
            if value > threshold:
                tally[name] += 1
    return str(max(tally, key=tally.__getitem__)) if tally else cand_names[0]


def winner_from_utilities(
    method: str,
    utilities: Dict[Any, Dict[str, float]],
    voters: List[Dict[str, Any]],
    cand_names: List[str],
) -> Optional[str]:
    """The winner under `method`, read off a voter -> candidate -> utility map.

    Raises `UnknownMethod` for a method outside UTILITY_METHODS: a caller that
    accepts a method name from a request should check it first and answer a bad
    one with a 400. These dispatchers used to end in `get_plurality_winner`,
    so /adaptive, /nota, /ballot-complexity and /electoral-fatigue all reported
    plurality's winner under whatever name was asked for.
    """
    if method == "approval":
        return sincere_approval_winner(utilities, voters, cand_names)
    if method == "majority_judgment":
        raw = get_majority_judgment_winner([utilities[v["id"]].copy() for v in voters])
        return str(raw["winner"]) if raw.get("winner") else None
    if method in SCORE_RULES:
        scores = [
            {n: max(0, min(5, round(5 * val))) for n, val in utilities[v["id"]].items()}
            for v in voters
        ]
        return rule_winner(method, scores=scores)
    return rule_winner(method, rankings_from_utilities(utilities, voters))
