"""S4.2 (docs/adr/ADR-009-ordinary-legislation.md): the policy status quo and the rules a
bill follows -- drafting, the assembly reading, the president's cohabitation block and the
sortition chamber's review. Pure functions over caller-assembled state; the tick phase that
runs them and journals what happened lives in run_polity_simulation.py.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from api.domain.polity.accountability import weighted_euclidean
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import LegislationConfig
from api.domain.polity.parties import Party

GOVERNMENT = "government"
PRESIDENT = "president"


@dataclass(frozen=True)
class Bill:
    bill_id: int
    agenda_setter: str
    """PRESIDENT or GOVERNMENT."""
    proposer: int
    """The president's citizen_id, or the government's initiating party_id."""
    dimensions: tuple[int, ...]
    proposal: tuple[float, ...]
    """The policy value the bill sets on each of `dimensions`."""
    returns_at_tick: int | None = None
    """Set once the chamber has vetoed it: when it returns for a second reading."""

    def enacted(self, policy: Sequence[float]) -> tuple[float, ...]:
        """`policy` with this bill's values in place."""
        values = dict(zip(self.dimensions, self.proposal))
        return tuple(values.get(d, value) for d, value in enumerate(policy))


@dataclass
class Legislature:
    """Everything legislation carries from tick to tick (checkpointed whole)."""

    policy: tuple[float, ...]
    seats: dict[int, int] | None = None
    """From the last legislative election; None before the first."""
    coalition: tuple[int, ...] | None = None
    """The governing coalition that election formed; None when none did."""
    policy_at_term_start: tuple[float, ...] | None = None
    """Policy when the sitting president's term began."""
    policy_at_assembly_start: tuple[float, ...] | None = None
    """Policy when the sitting assembly was elected."""
    suspended: Bill | None = None
    bills_drafted: int = 0
    bills_enacted: int = 0


def population_median(citizens: Sequence[Citizen]) -> tuple[float, ...]:
    """Each issue's median position across the population."""
    columns = zip(*(c.issue_positions for c in citizens))
    return tuple(_median(sorted(column)) for column in columns)


def _median(values: list[float]) -> float:
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def draft_bill(
    policy: Sequence[float], aim: Sequence[float], priorities: Sequence[float], config: LegislationConfig, *,
    bill_id: int, agenda_setter: str, proposer: int,
) -> Bill | None:
    """Move policy toward `aim` on the issues with the largest priority-weighted gap (at most
    max_bill_dimensions, ties to the lower issue), each by at most max_bill_step. None when
    policy already stands at the aim."""
    gaps = sorted(
        ((priority * abs(target - value), d) for d, (value, target, priority) in enumerate(zip(policy, aim, priorities))),
        key=lambda gap: (-gap[0], gap[1]),
    )
    dimensions = tuple(sorted(d for gap, d in gaps[:config.max_bill_dimensions] if gap > 0))
    if not dimensions:
        return None
    step = config.max_bill_step
    proposal = tuple(policy[d] + max(-step, min(step, aim[d] - policy[d])) for d in dimensions)
    return Bill(bill_id=bill_id, agenda_setter=agenda_setter, proposer=proposer, dimensions=dimensions, proposal=proposal)


@dataclass(frozen=True)
class AssemblyVote:
    yes_seats: int
    no_seats: int
    yes_parties: tuple[int, ...]
    passed: bool


def assembly_vote(
    parties: Sequence[Party], seats: Mapping[int, int], policy: Sequence[float], bill: Bill, majority_ratio: float,
) -> AssemblyVote:
    """Each seated party votes for the bill iff it brings policy strictly closer to its
    platform; the bill passes when the seats for it exceed majority_ratio of all seats."""
    enacted = bill.enacted(policy)
    yes = tuple(
        p.party_id for p in parties
        if seats.get(p.party_id, 0) > 0 and math.dist(p.platform, enacted) < math.dist(p.platform, policy)
    )
    yes_seats = sum(seats[pid] for pid in yes)
    total = sum(seats.values())
    return AssemblyVote(yes_seats=yes_seats, no_seats=total - yes_seats, yes_parties=yes, passed=yes_seats > majority_ratio * total)


def moves_away(position: Sequence[float], priorities: Sequence[float], policy: Sequence[float], bill: Bill) -> bool:
    """Does the bill leave policy farther from `position`, weighted by `priorities`?"""
    return weighted_euclidean(position, bill.enacted(policy), priorities) > weighted_euclidean(position, policy, priorities)


@dataclass(frozen=True)
class ChamberReview:
    yes: int
    no: int

    @property
    def rejects(self) -> bool:
        return self.no > self.yes


def chamber_review(members: Sequence[Citizen], policy: Sequence[float], bill: Bill) -> ChamberReview:
    """Each seated member votes for the bill iff it brings policy strictly closer to their
    chamber_position, weighted by their priorities."""
    enacted = bill.enacted(policy)
    yes = 0
    for member in members:
        position = member.chamber_position if member.chamber_position is not None else member.issue_positions
        yes += weighted_euclidean(position, enacted, member.issue_priorities) < weighted_euclidean(position, policy, member.issue_priorities)
    return ChamberReview(yes=yes, no=len(members) - yes)


@dataclass(frozen=True)
class Congruence:
    median_distance: float
    """RMS per-issue distance from policy to the population's median."""
    mean_citizen_distance: float
    """Mean distance from a citizen to policy, weighted by their priorities."""


def rms_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.dist(a, b) / math.sqrt(len(a)) if len(a) else 0.0


def congruence(citizens: Sequence[Citizen], policy: Sequence[float]) -> Congruence:
    return Congruence(
        median_distance=rms_distance(population_median(citizens), policy),
        mean_citizen_distance=sum(weighted_euclidean(c.issue_positions, policy, c.issue_priorities) for c in citizens) / max(len(citizens), 1),
    )
