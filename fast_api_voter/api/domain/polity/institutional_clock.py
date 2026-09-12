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

from api.domain.polity.config import InstitutionsConfig, RunConfig, SortitionChamberConfig


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
    # v6b Lot 2 (§6bis.3): always computed, regardless of whether
    # sortition_chamber.enabled is true -- cheap (one multiplication), and
    # gating happens at the call site, the same pattern president_term_ticks
    # etc. already use regardless of whether their own election mechanic is
    # itself enabled.
    sortition_term_ticks: int

    @classmethod
    def from_config(
        cls, institutions: InstitutionsConfig, run: RunConfig, sortition_chamber: SortitionChamberConfig,
    ) -> InstitutionalClock:
        return cls(
            president_term_ticks=institutions.president_term_years * run.ticks_per_year,
            assembly_term_ticks=institutions.assembly_term_years * run.ticks_per_year,
            assembly_offset_ticks=institutions.assembly_offset_years * run.ticks_per_year,
            total_ticks=run.total_ticks,
            sortition_term_ticks=sortition_chamber.term_years * run.ticks_per_year,
        )

    def is_presidential_election(self, tick: int) -> bool:
        return tick % self.president_term_ticks == 0

    def is_legislative_election(self, tick: int) -> bool:
        return (tick - self.assembly_offset_ticks) % self.assembly_term_ticks == 0

    def is_sortition_rotation(self, tick: int) -> bool:
        return tick % self.sortition_term_ticks == 0

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

    def is_presidential_declaration_tick(self, tick: int) -> bool:
        """Track E (2026-09-11): true exactly 2 ticks before a presidential
        election that has room to stagger into. The tick-0 election never
        has that room -- there is no tick -2 -- so it is excluded here
        rather than left for a caller to special-case; `_hold_presidential_
        election`'s own fallback (declare+nominate+position+vote in one
        tick, unchanged since v0) is what actually runs that election, the
        same as it always has. An election whose own tick would fall past
        `total_ticks` is excluded too -- it will never actually happen, so
        nothing should declare for it. Only meaningful when `institutions.
        staggered_election` is on; callers are expected to gate on that
        config flag themselves (this method has no config access)."""
        election_tick = tick + 2
        return election_tick >= 2 and election_tick <= self.total_ticks and self.is_presidential_election(election_tick)

    def is_presidential_nomination_tick(self, tick: int) -> bool:
        """Track E's own second stage -- true exactly 1 tick before the same
        elections `is_presidential_declaration_tick` covers, same
        exclusions, same reasoning."""
        election_tick = tick + 1
        return election_tick >= 2 and election_tick <= self.total_ticks and self.is_presidential_election(election_tick)

    def presidential_election_ticks(self) -> list[int]:
        return [t for t in range(self.total_ticks + 1) if self.is_presidential_election(t)]

    def legislative_election_ticks(self) -> list[int]:
        return [t for t in range(self.total_ticks + 1) if self.is_legislative_election(t)]
