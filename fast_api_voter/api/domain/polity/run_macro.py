"""A run's institutional story over time, for the run explorer's macro curves and
timeline: the sitting president's standing tick by tick, the mix of pressure citizens put
on them, each election's outcome with its turnout and blank share, the legislature's
blank rate, and the term bands with the institutional events laid over them.

A figure the journal does not hold stays None with its source named, never estimated:
blank share is exact when an invalidation check journaled it or every ballot was
journaled, a sample reading when only S4.1's audit ballots were, and unavailable
otherwise.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from api.domain.polity.codebook import PressureAct
from api.domain.polity.events import INSTITUTIONAL_EVENT_TYPES
from api.domain.polity.indexer import segment_terms

BlankSource = Literal["invalidation_check", "ballots", "audit_sample"]
ElectionOutcome = Literal["elected", "no_winner", "invalidated"]
Scalar = int | float | str | bool | None

_OUTCOMES: Mapping[str, ElectionOutcome] = {
    "elected": "elected", "election_no_winner": "no_winner", "election_invalidated": "invalidated",
}
TIMELINE_EVENT_TYPES = frozenset(INSTITUTIONAL_EVENT_TYPES | {"sortition_rotation"})


@dataclass(frozen=True)
class TickStanding:
    tick: int
    president: int | None
    legitimacy: float | None
    ecart: float | None
    mandate_strength: float | None
    acts: tuple[int, ...]
    """Pressure actions journaled this tick, counted by PressureAct code."""


@dataclass(frozen=True)
class ElectionPoint:
    tick: int
    outcome: ElectionOutcome
    winner: int | None
    forced: bool
    turnout: float | None
    """Share of the population casting a ballot; None when no vote was held or recorded."""
    blank_share: float | None
    blank_source: BlankSource | None


@dataclass(frozen=True)
class LegislativePoint:
    tick: int
    seats: Mapping[int, int]
    blank_rate: float | None


@dataclass(frozen=True)
class TermBand:
    holder: int
    start_tick: int
    end_tick: int
    ended_by: str
    lame_duck: bool
    mandate_strength: float | None


@dataclass(frozen=True)
class TimelineEntry:
    tick: int
    event_type: str
    citizen_id: int | None
    details: Mapping[str, Scalar]
    """The payload's scalar fields; lists and objects are left to the event log."""


@dataclass(frozen=True)
class RunMacro:
    standings: tuple[TickStanding, ...]
    elections: tuple[ElectionPoint, ...]
    legislative: tuple[LegislativePoint, ...]
    terms: tuple[TermBand, ...]
    timeline: tuple[TimelineEntry, ...]


def _by_tick(events: Sequence[Mapping[str, Any]]) -> dict[int, list[Mapping[str, Any]]]:
    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[int(event["tick"])].append(event)
    return grouped


def _standing(tick: int, events: Sequence[Mapping[str, Any]], president: int | None) -> TickStanding:
    readings = [e["payload"] for e in events if e["event_type"] == "legitimacy_updated" and e.get("citizen_id") == president]
    reading = readings[-1] if president is not None and readings else {}
    acts = Counter(int(e["payload"]["act"]) for e in events if e["event_type"] == "pressure_action")
    return TickStanding(
        tick=tick, president=president,
        legitimacy=reading.get("legitimacy"), ecart=reading.get("ecart"), mandate_strength=reading.get("mandate_strength"),
        acts=tuple(acts.get(int(act), 0) for act in PressureAct),
    )


def _blank_reading(outcome: Mapping[str, Any], events: Sequence[Mapping[str, Any]]) -> tuple[float | None, BlankSource | None]:
    if outcome["event_type"] == "election_invalidated":
        share = outcome["payload"].get("blank_share")
        return (float(share), "invalidation_check") if share is not None else (None, None)
    ballots = [e["payload"] for e in events if e["event_type"] == "vote_cast"]
    if not ballots:
        return None, None
    share = sum(1 for b in ballots if b["blank"]) / len(ballots)
    return share, "audit_sample" if any(b.get("audit") for b in ballots) else "ballots"


def _election(outcome: Mapping[str, Any], events: Sequence[Mapping[str, Any]], population: int) -> ElectionPoint:
    payload = outcome["payload"]
    held = outcome["event_type"] == "elected" or (outcome["event_type"] == "election_no_winner" and payload.get("reason") != "no_candidates")
    blank_share, blank_source = _blank_reading(outcome, events)
    return ElectionPoint(
        tick=int(outcome["tick"]),
        outcome=_OUTCOMES[outcome["event_type"]],
        winner=outcome.get("citizen_id") if outcome["event_type"] == "elected" else None,
        forced=bool(payload.get("forced")),
        turnout=1.0 - int(payload.get("abstained", 0)) / population if held else None,
        blank_share=blank_share,
        blank_source=blank_source,
    )


def _legislative(event: Mapping[str, Any]) -> LegislativePoint:
    payload = event["payload"]
    cast = sum(float(v) for v in payload["votes"].values()) + int(payload["blank_count"])
    return LegislativePoint(
        tick=int(event["tick"]),
        seats={int(party): int(seats) for party, seats in payload["seats"].items()},
        blank_rate=int(payload["blank_count"]) / cast if cast else None,
    )


def _timeline_entry(event: Mapping[str, Any]) -> TimelineEntry:
    payload = event.get("payload") or {}
    return TimelineEntry(
        tick=int(event["tick"]), event_type=str(event["event_type"]), citizen_id=event.get("citizen_id"),
        details={key: value for key, value in sorted(payload.items()) if isinstance(value, int | float | str | bool) or value is None},
    )


def build_macro(events: Sequence[Mapping[str, Any]], population: int, last_tick: int) -> RunMacro:
    terms = segment_terms(events, last_tick)
    by_tick = _by_tick(events)

    def president_at(tick: int) -> int | None:
        """A term covers [start, end); one still open when the run ended covers its last tick too."""
        return next((t.holder_id for t in terms
                     if t.start_tick <= tick < t.end_tick or (t.ended_by == "run_end" and tick == t.end_tick)), None)

    return RunMacro(
        standings=tuple(_standing(tick, by_tick.get(tick, []), president_at(tick)) for tick in range(last_tick + 1)),
        elections=tuple(
            _election(e, by_tick[int(e["tick"])], population) for e in events if e["event_type"] in _OUTCOMES
        ),
        legislative=tuple(_legislative(e) for e in events if e["event_type"] == "legislative_result"),
        terms=tuple(
            TermBand(holder=t.holder_id, start_tick=t.start_tick, end_tick=t.end_tick, ended_by=t.ended_by,
                     lame_duck=t.lame_duck, mandate_strength=t.mandate_strength)
            for t in terms
        ),
        timeline=tuple(_timeline_entry(e) for e in events if e["event_type"] in TIMELINE_EVENT_TYPES),
    )
