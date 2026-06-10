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
from typing import Any, Dict, List

from api.engine.constants import ECONOMY_ISSUES, ENV_ISSUES, SOCIAL_ISSUES

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


def inter_method_agreement(methods_data: Dict[str, Any]) -> float:
    """Fraction of voting methods that agree on the same winner (0..1)."""
    winners = [md.get("winner") for md in methods_data.values() if md.get("winner")]
    if not winners:
        return 0.0
    most_common = Counter(winners).most_common(1)[0][1]
    return round(most_common / len(winners), 4)
