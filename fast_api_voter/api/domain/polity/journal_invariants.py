"""api.domain.polity.journal_invariants -- the behaviour catalogue's event-level
invariants (docs/spec/behaviors.md), checked over a finished run's journal.

Each run-level test checks one invariant on one hand-picked config; this checks every
invariant a journal can show on its own, over any run, so a property test can draw
the run. A Violation names the catalogue ID it breaks. Pure: it reads the parsed
journal lines and the run's founding config, nothing else.

The journal must be a finished run's, from its first line: the election calendar is
replayed up to the config's last tick. A malformed line (a missing top-level field, or a
payload off its type) is reported under JRN-02 and left out of the other checks, so one
bad line never hides the rest of the report.

The calendar replay restates the simulator's scheduling rules from the journal's own
events rather than calling the simulator: an oracle that reused the code it checks would
agree with that code's bugs.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from api.domain.polity.config import PolityConfig
from api.domain.polity.events import PRESIDENT_ELECTION_OUTCOMES, validate_event
from api.domain.polity.institutional_clock import InstitutionalClock

Event = Mapping[str, Any]

SEATS_ARTICLE = "institutions.assembly_seats"


@dataclass(frozen=True)
class Violation:
    behavior: str  # the catalogue ID, e.g. "ELE-01"
    event_id: int | None  # the offending line, or None when no single line is
    message: str


def check_journal(events: Sequence[Event], config: PolityConfig) -> list[Violation]:
    """Every catalogue invariant this journal breaks; empty when it keeps them all."""
    sound = [event for event in events if not _missing_fields(event)]
    return [
        *sequential_ids(events),
        *valid_lines(events),
        *seats_allocated(sound, config),
        *legislative_calendar(sound, config),
        *presidential_calendar(sound, config),
        *elected_has_no_reason(events),
        *one_counted_vote(sound),
        *unit_interval(sound),
    ]


LINE_FIELDS: Mapping[str, type] = {"event_id": int, "tick": int, "event_type": str, "payload": dict}


def _missing_fields(event: Event) -> list[str]:
    """The top-level fields a line lacks (or carries with the wrong type): such a line is
    left out of every check but JRN-01/02. A line whose payload is off its type stays in,
    and the checks read its payload defensively."""
    return [name for name, kind in LINE_FIELDS.items() if not isinstance(event.get(name), kind)]


def sequential_ids(events: Sequence[Event]) -> Iterator[Violation]:
    """JRN-01: ids are 0, 1, 2... in write order."""
    for position, event in enumerate(events):
        if event.get("event_id") != position:
            yield Violation("JRN-01", event.get("event_id"), f"line {position} has event_id {event.get('event_id')!r}")


def valid_lines(events: Sequence[Event]) -> Iterator[Violation]:
    """JRN-02: every line has its top-level fields and validates against its registered
    type."""
    for event in events:
        missing = _missing_fields(event)
        if missing:
            yield Violation("JRN-02", event.get("event_id"), f"line without a valid {', '.join(missing)}")
            continue
        for problem in validate_event(event):
            yield Violation("JRN-02", event.get("event_id"), problem)


def seats_allocated(events: Sequence[Event], config: PolityConfig) -> Iterator[Violation]:
    """ELE-01: each legislative result allocates the assembly's seats in force, or none
    when no party clears the threshold (allocate_seats). An amendment of the seat count
    is written first in its tick (_phase_constitution) and governs the whole tick, so
    journal order gives the count in force."""
    seats = config.institutions.assembly_seats
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "constitution_amended" and payload.get("article") == SEATS_ARTICLE and "new" in payload:
            seats = payload["new"]
        elif event["event_type"] == "legislative_result" and isinstance(payload.get("seats"), dict):
            allocated = sum(payload["seats"].values())
            if allocated not in (seats, 0):
                yield Violation("ELE-01", event.get("event_id"), f"{allocated} seats allocated, {seats} in force")


def _clock(config: PolityConfig) -> InstitutionalClock:
    return InstitutionalClock.from_config(config.institutions, config.run, config.sortition_chamber)


def legislative_calendar(events: Sequence[Event], config: PolityConfig) -> Iterator[Violation]:
    """ELE-02, legislative half: one legislative result on each calendar tick, none
    elsewhere."""
    calendar = _clock(config).legislative_election_ticks()
    held = Counter(event["tick"] for event in events if event["event_type"] == "legislative_result")
    if held != Counter(calendar):
        yield Violation("ELE-02", None, f"legislative results on ticks {sorted(held.elements())}, calendar {calendar}")


def presidential_calendar(events: Sequence[Event], config: PolityConfig) -> Iterator[Violation]:
    """ELE-02, presidential half: one presidential outcome (PRESIDENT_ELECTION_OUTCOMES:
    elected, election_no_winner, election_invalidated) on each tick that holds a
    presidential election, none elsewhere.

    A presidential election is held on the calendar, except where a successful
    refuse_to_leave keeps the president on; while a rerun or snap election is pending,
    the calendar is suspended and the election is held on its next_attempt_tick
    instead (PendingRerun). Both are replayed from the journal's own events."""
    clock = _clock(config)
    by_tick: dict[int, list[Event]] = {}
    for event in events:
        by_tick.setdefault(event["tick"], []).append(event)
    calendar = set(clock.presidential_election_ticks())
    pending: int | None = None
    for tick in range(clock.total_ticks + 1):
        tick_events = by_tick.get(tick, [])
        if pending is not None:
            held = tick == pending
        else:
            held = tick in calendar and not any(_kept_in_office(event) for event in tick_events)
        outcomes = [event for event in tick_events if event["event_type"] in PRESIDENT_ELECTION_OUTCOMES]
        if len(outcomes) != int(held):
            yield Violation(
                "ELE-02", outcomes[0].get("event_id") if outcomes else None,
                f"tick {tick}: {len(outcomes)} presidential outcome(s), {int(held)} expected",
            )
        for event in tick_events:
            event_type = event["event_type"]
            if event_type in ("election_invalidated", "snap_election_triggered") and "next_attempt_tick" in event["payload"]:
                pending = event["payload"]["next_attempt_tick"]
            elif event_type in ("elected", "election_no_winner"):
                pending = None


def _kept_in_office(event: Event) -> bool:
    payload = event.get("payload") or {}
    return event.get("event_type") == "extra_legal_act" and payload.get("act") == "refuse_to_leave" and payload.get("success") == 1


def elected_has_no_reason(events: Sequence[Event]) -> Iterator[Violation]:
    """ELE-05: an `elected` event never carries a `reason` (JRN-02 also rejects the
    key; this names the invariant the reader cares about)."""
    for event in events:
        if event.get("event_type") == "elected" and "reason" in (event.get("payload") or {}):
            yield Violation("ELE-05", event.get("event_id"), "elected carries a reason")


def one_counted_vote(events: Sequence[Event]) -> Iterator[Violation]:
    """ELE-10: at most one counted vote_cast per citizen per tick (an audit ballot,
    journaled beside the utility vote, is never counted)."""
    seen: set[tuple[int, Any]] = set()
    for event in events:
        if event.get("event_type") != "vote_cast" or (event.get("payload") or {}).get("audit") == 1:
            continue
        key = (event["tick"], event.get("citizen_id"))
        if key in seen:
            yield Violation("ELE-10", event.get("event_id"), f"citizen {key[1]} cast a second counted vote on tick {key[0]}")
        seen.add(key)


UNIT_INTERVAL: Mapping[str, tuple[str, tuple[str, ...]]] = {
    "legitimacy_updated": ("CIT-01", ("legitimacy",)),
    "emotions_updated": ("CIT-10", ("anger", "anxiety", "enthusiasm")),
}


def unit_interval(events: Sequence[Event]) -> Iterator[Violation]:
    """CIT-01: the journaled legitimacy lies in [0, 1]. CIT-10: so do the journaled mean
    emotions."""
    for event in events:
        rule = UNIT_INTERVAL.get(str(event.get("event_type")))
        if rule is None:
            continue
        behavior, keys = rule
        payload = event.get("payload") or {}
        for key in keys:
            value = payload.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
                yield Violation(behavior, event.get("event_id"), f"{event.get('event_type')}.{key} = {value!r}")
