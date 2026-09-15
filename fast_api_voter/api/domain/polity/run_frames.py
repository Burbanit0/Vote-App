"""A finished run, tick by tick: who was an elector, a candidate or the president, who
sat in the chamber, and what each citizen did in that tick (design doc §16.4).

The yearly census (snapshots.jsonl) records every citizen's role and pledges at the start
of each year; between two censuses the journal is replayed, applying each event the way
run_polity_simulation applied the decision it records. Each year starts again from its
census, so a replay error cannot outlive the year it happens in -- and the oracle tests
replay whole runs without that reset and require the census and the final checkpoint to
come out exactly.

A frame is the state after its tick, plus what happened in it. Ticks after the last
checkpoint are marked partial: a crashed tick's events were journaled but never
confirmed. Event types this module does not know are listed, not fatal.
"""
from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from api.domain.polity.citizen import Office, Role
from api.domain.polity.events import ALL_EVENT_TYPES, PRESIDENT_ELECTION_OUTCOMES
from api.domain.polity.llm_behavior_engine import apply_shifts
from api.domain.polity.llm_schemas import PositionShift
from api.domain.polity.run_digest import read_journal_tolerant
from api.domain.polity.run_projection import Projection, build_projection

STATUS_CODES: Mapping[str, int] = {Role.ELECTOR.value: 0, Role.CANDIDATE.value: 1, Role.ELECTED.value: 2}
VOTE_NONE, VOTE_BLANK, VOTE_WINNER, VOTE_OTHER = -1, 0, 1, 2
CANDIDACY_NONE, CANDIDACY_DECLINED, CANDIDACY_DECLARED, CANDIDACY_NOMINATION_LOST, CANDIDACY_STANDING, CANDIDACY_ELECTED = (
    -1, 0, 1, 2, 3, 4,
)
ACT_NONE = -1

VoteCoverage = Literal["all", "audit_sample", "none"]

_ELECTION_OPENERS = frozenset({
    "candidacy_considered", "party_nomination_choice", "nomination_lost", "candidacy_declared", "campaign_positioning",
    "vote_cast", *PRESIDENT_ELECTION_OUTCOMES,
})


class NotExplorable(ValueError):
    """The run lacks what a replay needs: its config, its journal or its first census."""

    def __init__(self, run_dir: Path, reason: str) -> None:
        super().__init__(f"{run_dir}: {reason}")
        self.reason = reason


@dataclass
class CitizenState:
    role: str
    office: str
    pledged: tuple[float, ...] | None
    revealed: tuple[float, ...] | None

    @classmethod
    def from_census(cls, row: Mapping[str, Any]) -> CitizenState:
        return cls(role=row["role"], office=row["office"], pledged=_position(row.get("pledged_platform")),
                   revealed=_position(row.get("revealed_position")))


def _position(values: Sequence[float] | None) -> tuple[float, ...] | None:
    return tuple(float(v) for v in values) if values is not None else None


@dataclass
class ReplayState:
    citizens: list[CitizenState]
    chamber: set[int] = field(default_factory=set)
    readings: dict[int, dict[str, float]] = field(default_factory=dict)
    """holder -> the latest legitimacy, ecart and mandate strength journaled for them"""
    lame_duck: dict[int, bool] = field(default_factory=dict)

    @classmethod
    def from_census(cls, rows: Sequence[Mapping[str, Any]]) -> ReplayState:
        return cls(citizens=[CitizenState.from_census(row) for row in rows])

    def reset_to(self, rows: Sequence[Mapping[str, Any]]) -> None:
        """A new year: roles and pledges from its census; the chamber and readings carry on."""
        self.citizens = [CitizenState.from_census(row) for row in rows]

    def president(self) -> int | None:
        return next((cid for cid, citizen in enumerate(self.citizens) if citizen.office == Office.PRESIDENT.value), None)

    def vacate_president(self) -> None:
        """simple_rules.vacate_office: the outgoing holder is an elector again, pledges kept."""
        for citizen in self.citizens:
            if citizen.office == Office.PRESIDENT.value:
                citizen.role, citizen.office = Role.ELECTOR.value, Office.NONE.value


@dataclass
class TickMarks:
    """What each citizen did in one tick."""

    act: list[int]
    candidacy: list[int]
    ballots: dict[int, tuple[int, int | None]] = field(default_factory=dict)
    """voter -> (blank, first choice)"""
    winner: int | None = None
    audit_ballots: bool = False

    @classmethod
    def empty(cls, population: int) -> TickMarks:
        return cls(act=[ACT_NONE] * population, candidacy=[CANDIDACY_NONE] * population)

    def reach(self, citizen_id: int, stage: int) -> None:
        """The furthest candidacy stage reached this tick: a standing rupture candidate is
        still asked whether to declare, and may decline, then win."""
        self.candidacy[citizen_id] = max(self.candidacy[citizen_id], stage)

    def votes(self, population: int) -> list[int]:
        codes = [VOTE_NONE] * population
        for voter, (blank, first) in self.ballots.items():
            codes[voter] = VOTE_BLANK if blank else VOTE_WINNER if first is not None and first == self.winner else VOTE_OTHER
        return codes


Handler = Callable[[ReplayState, TickMarks, Mapping[str, Any], np.ndarray], None]


def _shifted(base: Sequence[float], shifts: Sequence[Mapping[str, Any]]) -> tuple[float, ...]:
    moves = [PositionShift.model_construct(dimension=int(s["dimension"]), delta=float(s["delta"])) for s in shifts]
    return apply_shifts(tuple(base), moves)


def _candidacy_considered(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    marks.reach(event["citizen_id"], CANDIDACY_DECLARED if event["payload"]["outcome"] == 1 else CANDIDACY_DECLINED)


def _candidacy_declared(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    """simple_rules.declare_candidacy: the candidate runs on their own view until positioned."""
    cid = event["citizen_id"]
    citizen = state.citizens[cid]
    citizen.role = Role.CANDIDATE.value
    citizen.pledged = citizen.revealed = tuple(float(v) for v in positions[cid])
    marks.reach(cid, CANDIDACY_STANDING)


def _nomination_lost(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    marks.reach(event["citizen_id"], CANDIDACY_NOMINATION_LOST)


def _campaign_positioning(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    cid = event["citizen_id"]
    citizen = state.citizens[cid]
    citizen.pledged = citizen.revealed = _shifted(positions[cid], event["payload"]["shifts"])


def _vote_cast(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    payload = event["payload"]
    ranking = payload.get("ranking") or []
    marks.ballots[event["citizen_id"]] = (int(payload["blank"]), int(ranking[0]) if ranking else None)
    marks.audit_ballots = marks.audit_ballots or bool(payload.get("audit"))


def _close_election(state: ReplayState, winner: int | None) -> None:
    """_hold_presidential_election's end: the winner takes office, every other candidate is
    an elector again with no pledge."""
    for cid, citizen in enumerate(state.citizens):
        if cid == winner:
            citizen.role, citizen.office = Role.ELECTED.value, Office.PRESIDENT.value
        elif citizen.role == Role.CANDIDATE.value:
            citizen.role, citizen.pledged, citizen.revealed = Role.ELECTOR.value, None, None


def _elected(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    marks.winner = event["citizen_id"]
    marks.reach(event["citizen_id"], CANDIDACY_ELECTED)
    _close_election(state, marks.winner)


def _no_winner(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    _close_election(state, None)


def _mandate_pledge_declared(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    """The winner's pledge, journaled in full -- exact even where positioning's base view
    was only known from the year's census."""
    cid = event["citizen_id"]
    citizen = state.citizens[cid]
    citizen.pledged = citizen.revealed = tuple(float(v) for v in event["payload"]["pledged_platform"])
    state.lame_duck[cid] = bool(event["payload"]["lame_duck"])


def _representative_response(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    citizen = state.citizens[event["citizen_id"]]
    assert citizen.revealed is not None, "a representative responds only with a pledge on record"
    citizen.revealed = _shifted(citizen.revealed, event["payload"]["shifts"])


def _recalled(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    citizen = state.citizens[event["citizen_id"]]
    citizen.role, citizen.office = Role.ELECTOR.value, Office.NONE.value


def _sortition_rotation(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    state.chamber = {int(cid) for cid in event["payload"]["seated"]}


def _pressure_action(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    marks.act[event["citizen_id"]] = int(event["payload"]["act"])


def _legitimacy_updated(state: ReplayState, marks: TickMarks, event: Mapping[str, Any], positions: np.ndarray) -> None:
    payload = event["payload"]
    state.readings[event["citizen_id"]] = {key: float(payload[key]) for key in ("legitimacy", "ecart", "mandate_strength")}


HANDLERS: Mapping[str, Handler] = {
    "candidacy_considered": _candidacy_considered,
    "candidacy_declared": _candidacy_declared,
    "nomination_lost": _nomination_lost,
    "campaign_positioning": _campaign_positioning,
    "vote_cast": _vote_cast,
    "elected": _elected,
    "election_no_winner": _no_winner,
    "election_invalidated": _no_winner,
    "mandate_pledge_declared": _mandate_pledge_declared,
    "representative_response": _representative_response,
    "recalled": _recalled,
    "sortition_rotation": _sortition_rotation,
    "pressure_action": _pressure_action,
    "legitimacy_updated": _legitimacy_updated,
}


def _election_opening(events: Sequence[Mapping[str, Any]]) -> int | None:
    """Where this tick's presidential election starts, when it holds one: the outgoing
    president leaves office there, before any candidacy of the election is declared. A
    rupture candidacy belongs to the earlier phase of the tick."""
    if not any(e["event_type"] in PRESIDENT_ELECTION_OUTCOMES for e in events):
        return None
    return next(
        i for i, e in enumerate(events)
        if e["event_type"] in _ELECTION_OPENERS and (e.get("payload") or {}).get("path") != "rupture"
    )


def replay(
    events: Sequence[Mapping[str, Any]], census: Mapping[int, Sequence[Mapping[str, Any]]], projection: Projection,
    ticks_per_year: int, *, reset_yearly: bool = True,
) -> Iterator[tuple[int, ReplayState, TickMarks]]:
    """(tick, state after it, what happened in it), from tick 0 to the journal's last tick.
    The yielded state is the live replay state: read it before advancing."""
    by_tick: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        by_tick[int(event["tick"])].append(event)
    state = ReplayState.from_census(census[0])
    population = len(state.citizens)
    for tick in range(max(by_tick, default=-1) + 1):
        year = tick // ticks_per_year
        if reset_yearly and tick > 0 and tick % ticks_per_year == 0 and year in census:
            state.reset_to(census[year])
        positions = projection.issue_positions[projection.census_year(year)]
        marks = TickMarks.empty(population)
        tick_events = by_tick.get(tick, [])
        opening = _election_opening(tick_events)
        for index, event in enumerate(tick_events):
            if index == opening:
                state.vacate_president()
            handler = HANDLERS.get(event["event_type"])
            if handler is not None:
                handler(state, marks, event, positions)
        yield tick, state, marks


@dataclass(frozen=True)
class PresidentState:
    citizen_id: int
    xy: tuple[float, float]
    pledged_xy: tuple[float, float] | None
    legitimacy: float | None
    ecart: float | None
    mandate_strength: float | None
    lame_duck: bool


@dataclass(frozen=True)
class TickFrame:
    tick: int
    partial: bool
    status: tuple[int, ...]
    chamber: tuple[int, ...]
    act: tuple[int, ...]
    vote: tuple[int, ...]
    candidacy: tuple[int, ...]
    president: PresidentState | None


@dataclass(frozen=True)
class RunFrames:
    run_id: str
    population: int
    ticks_per_year: int
    last_checkpoint_tick: int | None
    vote_coverage: VoteCoverage
    projection: Projection
    frames: tuple[TickFrame, ...]
    unknown_event_types: tuple[str, ...]


def _president_state(state: ReplayState, projection: Projection, year: int) -> PresidentState | None:
    cid = state.president()
    if cid is None:
        return None
    citizen = state.citizens[cid]
    xy = projection.holder_xy(cid, year, citizen.revealed) if citizen.revealed is not None else _citizen_xy(projection, cid, year)
    reading = state.readings.get(cid, {})
    return PresidentState(
        citizen_id=cid, xy=xy,
        pledged_xy=projection.holder_xy(cid, year, citizen.pledged) if citizen.pledged is not None else None,
        legitimacy=reading.get("legitimacy"), ecart=reading.get("ecart"), mandate_strength=reading.get("mandate_strength"),
        lame_duck=state.lame_duck.get(cid, False),
    )


def _citizen_xy(projection: Projection, cid: int, year: int) -> tuple[float, float]:
    x, y = projection.citizens_at(year)[cid]
    return float(x), float(y)


def build_frames(
    events: Sequence[Mapping[str, Any]], census: Mapping[int, Sequence[Mapping[str, Any]]], projection: Projection,
    ticks_per_year: int, last_checkpoint_tick: int | None,
) -> tuple[tuple[TickFrame, ...], bool]:
    """Every tick's frame, and whether any ballot was an audit ballot."""
    frames = []
    audited = False
    for tick, state, marks in replay(events, census, projection, ticks_per_year):
        population = len(state.citizens)
        audited = audited or marks.audit_ballots
        frames.append(TickFrame(
            tick=tick,
            partial=last_checkpoint_tick is None or tick > last_checkpoint_tick,
            status=tuple(STATUS_CODES[c.role] for c in state.citizens),
            chamber=tuple(int(cid in state.chamber) for cid in range(population)),
            act=tuple(marks.act), vote=tuple(marks.votes(population)), candidacy=tuple(marks.candidacy),
            president=_president_state(state, projection, tick // ticks_per_year),
        ))
    return tuple(frames), audited


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def census_by_year(rows: Sequence[Mapping[str, Any]], population: int) -> dict[int, list[dict[str, Any]]]:
    """Complete census years only, each ordered by citizen_id: a year cut short by an
    interrupted write is dropped."""
    years: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        years[int(row["year"])].append(dict(row))
    return {
        year: sorted(year_rows, key=lambda row: int(row["citizen_id"]))
        for year, year_rows in sorted(years.items())
        if len(year_rows) == population
    }


def read_rows(path: Path) -> list[dict[str, Any]]:
    """A JSONL file's rows, a torn final row skipped; none when the file is missing."""
    rows = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def read_census(path: Path, population: int) -> dict[int, list[dict[str, Any]]]:
    return census_by_year(read_rows(path), population)


def _vote_coverage(events: Sequence[Mapping[str, Any]], audited: bool) -> VoteCoverage:
    if not any(e["event_type"] == "vote_cast" for e in events):
        return "none"
    return "audit_sample" if audited else "all"


def _last_checkpoint_tick(run_dir: Path) -> int | None:
    progress = _read_json(run_dir / "progress.json") or {}
    tick = progress.get("last_checkpoint_tick")
    return int(tick) if isinstance(tick, int) else None


def load_run_frames(run_dir: Path) -> RunFrames:
    events, _skipped = read_journal_tolerant(run_dir / "events.jsonl")
    return frames_for(run_dir, events, read_rows(run_dir / "snapshots.jsonl"))


def frames_for(run_dir: Path, events: Sequence[Mapping[str, Any]], snapshot_rows: Sequence[Mapping[str, Any]]) -> RunFrames:
    """The frames of the run in `run_dir`, from its journal and census rows already read."""
    config = _read_json(run_dir / "config.json")
    if config is None:
        raise NotExplorable(run_dir, "no readable config.json")
    run = config["run"]
    population, ticks_per_year = int(run["population_size"]), int(run["ticks_per_year"])
    if not events:
        raise NotExplorable(run_dir, "no journal")
    census = census_by_year(snapshot_rows, population)
    if 0 not in census:
        raise NotExplorable(run_dir, "no complete year-0 census")
    projection = build_projection(config, census)
    last_checkpoint = _last_checkpoint_tick(run_dir)
    frames, audited = build_frames(events, census, projection, ticks_per_year, last_checkpoint)
    return RunFrames(
        run_id=str(events[0].get("run_id", run_dir.name)),
        population=population,
        ticks_per_year=ticks_per_year,
        last_checkpoint_tick=last_checkpoint,
        vote_coverage=_vote_coverage(events, audited),
        projection=projection,
        frames=frames,
        unknown_event_types=tuple(sorted({str(e["event_type"]) for e in events} - ALL_EVENT_TYPES)),
    )
