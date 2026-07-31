"""
api.domain.polity.institutional_clock — the electoral calendar (Lot 4,
design doc §6).

The valid tick domain is [0, total_ticks] INCLUSIVE: tick 0 is the start of
year 0, tick `total_ticks` is the end of the last simulated year. This is
what makes the default config (4-year terms, a 2-year assembly offset, a
30-year run) reproduce exactly the two calendars given as the worked example
in §6 — presidential at years 0,4,...,28 and legislative at years
2,6,...,30 — which lands on ticks 0..112 and 8..120 respectively, 8 of each.
A half-open [0, total_ticks) domain would silently drop the last legislative
election (120 ≡ 8 mod 16, the same residue as the assembly offset — an
interval whose length is an exact multiple of the term always shorts one of
the two residue classes at the boundary).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from api.domain.polity.config import InstitutionsConfig, RunConfig


class ElectionType(str, Enum):
    NONE = "none"
    PRESIDENTIAL = "presidential"
    LEGISLATIVE = "legislative"
    BOTH = "both"


@dataclass(frozen=True)
class InstitutionalClock:
    president_term_ticks: int
    assembly_term_ticks: int
    assembly_offset_ticks: int
    total_ticks: int

    @classmethod
    def from_config(cls, institutions: InstitutionsConfig, run: RunConfig) -> InstitutionalClock:
        return cls(
            president_term_ticks=institutions.president_term_years * run.ticks_per_year,
            assembly_term_ticks=institutions.assembly_term_years * run.ticks_per_year,
            assembly_offset_ticks=institutions.assembly_offset_years * run.ticks_per_year,
            total_ticks=run.total_ticks,
        )

    def is_presidential_election(self, tick: int) -> bool:
        return tick % self.president_term_ticks == 0

    def is_legislative_election(self, tick: int) -> bool:
        return (tick - self.assembly_offset_ticks) % self.assembly_term_ticks == 0

    def election_at(self, tick: int) -> ElectionType:
        presidential = self.is_presidential_election(tick)
        legislative = self.is_legislative_election(tick)
        if presidential and legislative:
            return ElectionType.BOTH
        if presidential:
            return ElectionType.PRESIDENTIAL
        if legislative:
            return ElectionType.LEGISLATIVE
        return ElectionType.NONE

    def presidential_election_ticks(self) -> list[int]:
        return [t for t in range(self.total_ticks + 1) if self.is_presidential_election(t)]

    def legislative_election_ticks(self) -> list[int]:
        return [t for t in range(self.total_ticks + 1) if self.is_legislative_election(t)]
