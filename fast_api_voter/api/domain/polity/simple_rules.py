"""
api.domain.polity.simple_rules — the v0/v1 deterministic decision baseline
(Lot 6, resolves audit blocker A5; rupture path added for v1).

Three rules, each isolated and independently testable, matching
DEMARRAGE-polity-v0.md §2 and audit-precision-plan.md A5:

1. Vote: nearest candidate by issue-priority-weighted distance; blank if
   even the nearest candidate is farther than the voter's own tolerance.
2. Candidacy: `decide_candidacy` is design doc §2.4's dominant path
   (ambition-score threshold), used to filter party nominees. The rare
   "candidature de rupture" path (§2.4) is a separate function,
   `attempt_rupture_candidacy` — independent of perceived support by
   design, so it does not reuse `decide_candidacy` at all.
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

import numpy as np

from api.domain.polity.citizen import Citizen, Office, Role
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


def choose_party(voter: Citizen, parties: list[Party]) -> int | None:
    """Party-list analogue of build_ranking's vote rule (A5), for the
    legislative election (assembly_mode: party_list): nearest party
    platform by issue-priority-weighted distance, or blank (None) if even
    the nearest party is farther than the voter's own tolerance. Ties
    broken by the lowest party_id."""
    nearest = min(
        parties, key=lambda p: (_weighted_distance(voter, p.platform), p.party_id)
    )
    if _weighted_distance(voter, nearest.platform) > voter.blank_threshold:
        return None
    return nearest.party_id


# ── 2. Candidacy rule ─────────────────────────────────────────────────────

def decide_candidacy(citizen: Citizen, config: CandidacyConfig) -> bool:
    """Design doc §2.4 dominant path: ambition_score crosses a fixed
    threshold. The rare rupture path (attempt_rupture_candidacy, below) is
    entirely separate — it is independent of perceived support by design,
    so it never calls this function."""
    return citizen.ambition_score >= config.ambition_threshold


def sympathizer_ratio(citizen: Citizen, population: list[Citizen]) -> float:
    """Proxy for "parrainages simulés" (§2.3): the fraction of the
    population who would sincerely consider `citizen` an acceptable choice
    (within their own blank_threshold), reusing the same tolerance concept
    already used for voting rather than inventing a new one. No social graph
    to ground "simulated signatures"/"perceived support" more directly.

    Public (not module-private) since v2 increment 2: also the "perceived
    support" input signal llm_behavior_engine.decide_candidacies gives the
    LLM for the dominant candidacy path, alongside its existing use as the
    rupture path's signature-ratio gate below."""
    sympathizers = sum(
        1 for other in population
        if _weighted_distance(other, citizen.issue_positions) <= other.blank_threshold
    )
    return sympathizers / len(population)


def attempt_rupture_candidacy(
    citizen: Citizen,
    population: list[Citizen],
    config: CandidacyConfig,
    rng: np.random.Generator,
) -> bool:
    """Design doc §2.4 rare path: a citizen may declare independently of
    perceived support, gated only by a flat per-tick draw
    (rupture_base_probability) and a reduced signature bar
    (rupture_signature_ratio) — never by ambition_score or by
    decide_candidacy. The RNG is always drawn from when the path is
    enabled (win or lose the coin flip) so draw order — and therefore
    reproducibility — never depends on the outcome.

    The "quelle fonction de l'écart idéologique" question left open in the
    design doc (§2.4, Points ouverts #1) is deliberately NOT answered here:
    eligibility does not depend on ideological distance to any incumbent
    or party — only on the flat probability already pinned in config. v1
    ships the literal, minimal reading of the config; a distance-weighted
    eligibility function is left to a later palier.
    """
    if not config.rupture_path_enabled:
        return False
    if rng.random() >= config.rupture_base_probability:
        return False
    return sympathizer_ratio(citizen, population) >= config.rupture_signature_ratio


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


def select_party_nominee_from_declared(
    party_id: int, citizens: list[Citizen], declared_cids: set[int]
) -> Citizen | None:
    """v2 increment 2's LLM-path counterpart to select_party_nominee: same
    filter shape (party match) and same tiebreak (highest ambition_score,
    lowest citizen_id), but eligibility comes from decide_candidacies'
    outcome=1 set instead of decide_candidacy's bare threshold —
    party_nomination_choice itself (design doc dt=4, arbitrating among
    several eligible members) stays this increment's deterministic tiebreak,
    out of scope for the LLM. select_party_nominee/decide_candidacy stay
    untouched, still the baseline for §11.4's comparison."""
    eligible = [c for c in citizens if c.party_affiliation == party_id and c.citizen_id in declared_cids]
    if not eligible:
        return None
    return max(eligible, key=lambda c: (c.ambition_score, -c.citizen_id))


def vacate_office(citizen: Citizen) -> None:
    """v4 Lot 2: extracted from _hold_presidential_election's inline reset
    (PR #130) -- needed at three call sites once Lot 3 (floor recall) and
    Lot 5 (lost confidence vote) exist, and three divergent copies is
    exactly how PR #130's bug came back the first time."""
    citizen.role = Role.ELECTOR
    citizen.office = Office.NONE
    citizen.term_end_tick = None


def declare_candidacy(citizen: Citizen) -> None:
    """v0 has no campaign strategizing: a candidate runs on their own
    sincere position. revealed_position is pinned equal to pledged_platform
    (design doc §7bis.5) — the deviation this enables is a v2+ LLM effect,
    zero by construction here."""
    citizen.role = Role.CANDIDATE
    citizen.pledged_platform = citizen.issue_positions
    citizen.revealed_position = citizen.issue_positions


# ── 3. Coalition rule ─────────────────────────────────────────────────────

def tiebreak_key(
    party_id: int, seats: dict[int, int], votes: dict[int, float], tiebreak: tuple[str, ...]
) -> tuple[float, ...]:
    """Public since v2 increment 5: also the initiator-designation rule
    llm_behavior_engine.decide_coalition reuses, so the LLM path and the
    deterministic baseline designate the same formateur (§3.7.1's `action=4
    propose` stays reserved-but-unused — see CoalitionAction, codebook.py)."""
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

    initiator = min(governing, key=lambda pid: tiebreak_key(pid, seats, votes, tiebreak))
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
