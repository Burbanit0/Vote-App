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
class Phase:
    """One tick's place in the political calendar (S4.4, InstitutionalClock.phase)."""

    election: ElectionType
    """The election held this tick, if any."""
    presidential_campaign: bool
    legislative_campaign: bool
    ticks_to_presidential: int | None
    """Ticks until the next presidential election the run reaches: 0 on its tick, None past the last."""
    ticks_to_legislative: int | None

    @property
    def name(self) -> str:
        if self.election is not ElectionType.NONE:
            return "election"
        if self.presidential_campaign or self.legislative_campaign:
            return "campaign"
        return "governing"


def _in_window(ticks_to: int | None, window: int) -> bool:
    return ticks_to is not None and 0 < ticks_to <= window


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
    # S4.4: how many ticks before each election its campaign runs (see phase()).
    presidential_campaign_ticks: int = 0
    legislative_campaign_ticks: int = 0

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
            presidential_campaign_ticks=institutions.presidential_campaign_ticks,
            legislative_campaign_ticks=institutions.legislative_campaign_ticks,
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

    def _next_election(self, tick: int, term_ticks: int, offset_ticks: int) -> int | None:
        """The first election tick on this calendar at or after `tick`, or None when it
        falls past the run's end (or `tick` is before the run starts)."""
        if tick < 0:
            return None
        election_tick = offset_ticks + term_ticks * -((offset_ticks - tick) // term_ticks)
        return election_tick if election_tick <= self.total_ticks else None

    def ticks_to_presidential(self, tick: int) -> int | None:
        election_tick = self._next_election(tick, self.president_term_ticks, 0)
        return None if election_tick is None else election_tick - tick

    def ticks_to_legislative(self, tick: int) -> int | None:
        election_tick = self._next_election(tick, self.assembly_term_ticks, self.assembly_offset_ticks)
        return None if election_tick is None else election_tick - tick

    def phase(self, tick: int) -> Phase:
        """S4.4: where the political calendar stands at `tick` -- a pure function of the
        tick, so any reader with the calendar can compute it and nothing journals it. A
        campaign is the `*_campaign_ticks` ticks before an election that the run reaches;
        the tick-0 election has none. Presidential and legislative campaigns can overlap."""
        to_presidential = self.ticks_to_presidential(tick)
        to_legislative = self.ticks_to_legislative(tick)
        return Phase(
            election=self.election_at(tick),
            presidential_campaign=_in_window(to_presidential, self.presidential_campaign_ticks),
            legislative_campaign=_in_window(to_legislative, self.legislative_campaign_ticks),
            ticks_to_presidential=to_presidential,
            ticks_to_legislative=to_legislative,
        )

    def _staggering_window(self) -> int:
        """The presidential campaign a staggered election spreads over, never reaching back
        to the previous presidential election's own tick."""
        return min(self.presidential_campaign_ticks, self.president_term_ticks - 1)

    def is_presidential_declaration_tick(self, tick: int) -> bool:
        """Track E, absorbed by S4.4: the first tick of a presidential campaign, where a
        staggered election declares candidacies. The tick-0 election has no campaign, so it
        stays atomic -- `_hold_presidential_election` declares, nominates, positions and
        votes in one tick, as it always has -- and an election past `total_ticks` gets
        none either. Only meaningful when `institutions.staggered_election` is on; callers
        gate on that flag (this class has no config access)."""
        window = self._staggering_window()
        return window > 0 and self.ticks_to_presidential(tick) == window

    def is_presidential_nomination_tick(self, tick: int) -> bool:
        """The campaign's last tick, where a staggered election nominates and positions --
        the same tick as the declaration when the campaign is one tick long."""
        return self._staggering_window() > 0 and self.ticks_to_presidential(tick) == 1

    def presidential_election_ticks(self) -> list[int]:
        return [t for t in range(self.total_ticks + 1) if self.is_presidential_election(t)]

    def legislative_election_ticks(self) -> list[int]:
        return [t for t in range(self.total_ticks + 1) if self.is_legislative_election(t)]
