"""
api.domain.polity.simple_rules — the v0/v1 deterministic decision baseline
(Lot 6, resolves audit blocker A5).

Three rules, each isolated and independently testable, matching
DEMARRAGE-polity-v0.md §2 and audit-precision-plan.md A5:

1. Vote: nearest candidate by issue-priority-weighted distance; blank if
   even the nearest candidate is farther than the voter's own tolerance.
2. Candidacy: an ambition-score threshold (v0 only implements the dominant
   path of design doc §2.4 — the rare "candidature de rupture" path is
   disabled in v0's config and raises if ever turned on without v1's
   implementation).
3. Coalition: nearest-ideological-neighbour aggregation until a majority of
   seats is reached, with every tiebreak explicit (DEMARRAGE §4) — a bare
   max()/min() on insertion order would make the byte-for-byte
   reproducibility test (Lot 8) depend on an implementation accident.

This module is deliberately what llm_behavior_engine.py replaces in v2 — it
also stays on afterwards as the baseline against which the LLM's effect is
measured (§11.1 of the design doc): in v0/v1, mandate deviation is zero by
construction, since a candidate's revealed_position never diverges from
their pledged_platform.
"""
from __future__ import annotations

import math

from api.domain.polity.citizen import Citizen, Role
from api.domain.polity.config import CandidacyConfig
from api.domain.polity.parties import Party

CANDIDATE_LABEL_PREFIX = "citizen_"
BLANK_LABEL = "Blank"


def candidate_label(citizen: Citizen) -> str:
    return f"{CANDIDATE_LABEL_PREFIX}{citizen.citizen_id}"


def citizen_id_from_label(label: str) -> int:
    return int(label[len(CANDIDATE_LABEL_PREFIX):])


# ── 1. Vote rule ──────────────────────────────────────────────────────────

def _weighted_distance(voter: Citizen, platform: tuple[float, ...]) -> float:
    """Euclidean distance weighted by the voter's own issue_priorities —
    positions live in [0, 1] per dimension and priorities sum to 1, so the
    result stays in [0, 1], comparable to blank_threshold."""
    return math.sqrt(
        sum(
            weight * (voter_x - platform_x) ** 2
            for voter_x, platform_x, weight in zip(
                voter.issue_positions, platform, voter.issue_priorities
            )
        )
    )


def _candidate_platform(candidate: Citizen) -> tuple[float, ...]:
    if candidate.pledged_platform is None:
        raise ValueError(f"citizen {candidate.citizen_id} has not declared a candidacy")
    return candidate.pledged_platform


def build_ranking(
    voter: Citizen, candidates: list[Citizen], blank_label: str = BLANK_LABEL
) -> list[str]:
    """A sincere ranking for `voter` over `candidates`, blank spliced in.

    Mirrors simulation_metrics._insert_blank, with distance standing in for
    utility (lower is better instead of higher): candidates within the
    voter's blank_threshold are ranked above blank in ascending-distance
    order, candidates beyond it below. Ties in distance are broken by the
    lowest citizen_id — an explicit, deterministic tiebreak, never
    insertion order.
    """
    ranked = sorted(
        candidates,
        key=lambda c: (_weighted_distance(voter, _candidate_platform(c)), c.citizen_id),
    )
    names = [candidate_label(c) for c in ranked]
    within_tolerance = sum(
        1 for c in ranked if _weighted_distance(voter, _candidate_platform(c)) <= voter.blank_threshold
    )
    return names[:within_tolerance] + [blank_label] + names[within_tolerance:]


# ── Party affiliation (the natural complement to Lot 3's k-means platforms:
#    a citizen's initial party is whichever platform sits closest to them) ──

def assign_party_affiliation(citizen: Citizen, parties: list[Party]) -> int:
    return min(
        parties, key=lambda p: (math.dist(citizen.issue_positions, p.platform), p.party_id)
    ).party_id


# ── 2. Candidacy rule ─────────────────────────────────────────────────────

def decide_candidacy(citizen: Citizen, config: CandidacyConfig) -> bool:
    """Design doc §2.4 dominant path only: ambition_score crosses a fixed
    threshold. The rare rupture path is a v1 feature (config.
    rupture_path_enabled is false in v0); this raises rather than silently
    no-op if it is ever turned on before it is implemented."""
    if config.rupture_path_enabled:
        raise NotImplementedError("candidacy rupture path (design doc §2.4) is not implemented before v1")
    return citizen.ambition_score >= config.ambition_threshold


def select_party_nominee(
    party_id: int, citizens: list[Citizen], config: CandidacyConfig
) -> Citizen | None:
    """Design doc §2.3: a party nominates exactly one candidate among its
    ambitious members. v0 has no LLM to arbitrate (§3.6.3 is v2+), so the
    nominee is the eligible citizen with the highest ambition_score, ties
    broken by the lowest citizen_id. Returns None if no member of this
    party clears the candidacy threshold this cycle."""
    eligible = [
        c for c in citizens if c.party_affiliation == party_id and decide_candidacy(c, config)
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda c: (c.ambition_score, -c.citizen_id))


def declare_candidacy(citizen: Citizen) -> None:
    """v0 has no campaign strategizing: a candidate runs on their own
    sincere position. revealed_position is pinned equal to pledged_platform
    (design doc §7bis.5) — the deviation this enables is a v2+ LLM effect,
    zero by construction here."""
    citizen.role = Role.CANDIDATE
    citizen.pledged_platform = citizen.issue_positions
    citizen.revealed_position = citizen.issue_positions


# ── 3. Coalition rule ─────────────────────────────────────────────────────

def _tiebreak_key(
    party_id: int, seats: dict[int, int], votes: dict[int, float], tiebreak: tuple[str, ...]
) -> tuple[float, ...]:
    key: list[float] = []
    for criterion in tiebreak:
        if criterion == "seats":
            key.append(-float(seats.get(party_id, 0)))
        elif criterion == "votes":
            key.append(-float(votes.get(party_id, 0.0)))
        else:  # "party_id" — config.py already validated no other value can appear
            key.append(float(party_id))
    return tuple(key)


def form_coalition(
    party_platforms: dict[int, tuple[float, ...]],
    seats: dict[int, int],
    votes: dict[int, float],
    tiebreak: tuple[str, ...],
    majority_ratio: float,
) -> list[int] | None:
    """DEMARRAGE-polity-v0.md §4 — nearest-ideological-neighbour coalition
    formation. Returns the ordered list of party_ids in the governing
    coalition, or None if no coalition reaches a majority even after every
    seated party is added (§4 point 3 — journal as `coalition_failed`;
    logging is the caller's job, this function only reports the outcome).

    1. Initiator = the seated party ranked first by `tiebreak` (config:
       [seats, votes, party_id] — every level explicit, never a bare
       max()/min() on dict insertion order).
    2. Remaining seated parties are added in ascending distance from the
       initiator's platform until the coalition crosses `majority_ratio`
       of all seats; ties in distance broken by seats descending, then
       party_id (this second cascade never includes votes — a distinct,
       fixed rule from the initiator's).
    """
    governing = [pid for pid, s in seats.items() if s > 0]
    if not governing:
        return None

    total_seats = sum(seats.values())
    majority_threshold = majority_ratio * total_seats

    initiator = min(governing, key=lambda pid: _tiebreak_key(pid, seats, votes, tiebreak))
    coalition = [initiator]
    coalition_seats = seats[initiator]
    if coalition_seats > majority_threshold:
        return coalition

    remaining = [pid for pid in governing if pid != initiator]
    remaining.sort(
        key=lambda pid: (
            math.dist(party_platforms[pid], party_platforms[initiator]),
            -seats[pid],
            pid,
        )
    )
    for pid in remaining:
        coalition.append(pid)
        coalition_seats += seats[pid]
        if coalition_seats > majority_threshold:
            return coalition

    return None
