"""Workers for /api/v2/polity/* (the run explorer): each takes the explorer's context and
the request's parameters and returns `(body, http_status)`, the domain-worker contract
the routes lift into responses (api/core/worker_dispatch.py).

Bodies carry run keys and paths relative to a run root, never an absolute path. Map
coordinates are rounded to four decimals: the page draws them, it does not compute with
them, and a population-500 run's frames stay small.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from api.domain.polity.codebook import motif_labels
from api.domain.polity.run_catalog import (
    DEFAULT_RUN_ROOT,
    CatalogEntry,
    LoadedRun,
    RunCache,
    RunRoot,
    find_run,
    list_runs,
    parse_roots,
)
from api.domain.polity.run_frames import NotExplorable, TickFrame
from api.domain.polity.run_projection import Projection
from api.engine.utils.logger import get_logger

_log = get_logger(__name__)

MAX_FRAME_SPAN = 40
XY_DECIMALS = 4

Body = tuple[dict[str, Any], int]


@dataclass(frozen=True)
class ExplorerContext:
    roots: tuple[RunRoot, ...]
    max_journal_bytes: int
    cache: RunCache


def explorer_roots(spec: str) -> tuple[RunRoot, ...]:
    """The configured roots, or the committed fixture run's when none are."""
    return parse_roots(spec) or (RunRoot(label="fixture", path=DEFAULT_RUN_ROOT),)


def _xy(point: Sequence[float]) -> list[float]:
    return [round(float(point[0]), XY_DECIMALS), round(float(point[1]), XY_DECIMALS)]


def _as_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def list_polity_runs(context: ExplorerContext) -> Body:
    """Every run the explorer can open.

    A run record is built from whatever its own files hold, and `run_registry` is
    deliberate about never raising on a damaged run ("a registry that crashes on one
    damaged run lists none"). The strict response model would undo that, so each field
    is narrowed to what the schema declares here: one run with a population of
    "quarante" costs that run its shape, not everybody else their listing.
    """
    runs = []
    for entry in list_runs(context.roots, context.max_journal_bytes):
        record = entry.record
        runs.append({
            "key": entry.key, "label": entry.label, "relative_path": entry.relative_path, "run_id": str(record["run_id"]),
            "generation": str(record["generation"]),
            **{field: _as_str(record.get(field)) for field in ("engine", "outcome")},
            **{field: _as_int(record.get(field)) for field in (
                "population", "years", "seed", "ticks_reached", "ticks_planned")},
        })
    return {"runs": runs}, 200


class _Refused(Exception):
    def __init__(self, error: str, status: int) -> None:
        super().__init__(error)
        self.body: Body = ({"error": error}, status)


def _load(context: ExplorerContext, run_key: str) -> tuple[CatalogEntry, LoadedRun]:
    """The run behind a key, loaded once and cached.

    A run root is a directory a batch wrote, not a validated payload: a listed run can
    still turn out to be unreadable (a config without a `run` section, a population that
    is a word, a census row missing a field). That is a 400 about that run, not a 500
    about the server, so the replay's own failures are mapped here rather than escaping
    as an unhandled exception. They are logged, since a shape the replay cannot read is
    worth seeing even when the answer to the caller is short.
    """
    entry = find_run(context.roots, run_key, context.max_journal_bytes)
    if entry is None:
        raise _Refused("run not found", 404)
    try:
        return entry, context.cache.get(entry.run_dir)
    except NotExplorable as exc:
        raise _Refused(f"run cannot be explored: {exc.reason}", 400) from exc
    except OSError as exc:
        _log.warning("polity run %s could not be read: %s", entry.relative_path, exc)
        raise _Refused("run cannot be explored: its files could not be read", 400) from exc
    except (ArithmeticError, AssertionError, LookupError, TypeError, ValueError) as exc:
        _log.warning("polity run %s is not the shape the replay expects", entry.relative_path, exc_info=True)
        raise _Refused("run cannot be explored: its files are not the shape the replay expects", 400) from exc


def _plain(value: Any) -> Any:
    return dataclasses.asdict(value)


def _party(projection: Projection, party_id: int, platform: Sequence[float]) -> dict[str, Any] | None:
    """A party's marker on the map, or None when its platform cannot be placed there.

    A checkpoint written by another engine version can hold a platform of a different
    length than the run's issues, which no projection can place. The map then shows the
    citizens without that party's marker, rather than the page failing.
    """
    try:
        return {"party_id": party_id, "xy": _xy(projection.point_xy(platform))}
    except (AssertionError, ValueError):
        _log.warning("polity party %s has a platform the projection cannot place", party_id)
        return None


def _map(loaded: LoadedRun) -> dict[str, Any]:
    """Where citizens and parties sit, and each citizen's party."""
    projection = loaded.frames.projection
    census_zero = sorted((r for r in loaded.view.snapshots if r.get("year") == 0), key=lambda r: int(r["citizen_id"]))
    return {
        "projection": {
            "method": projection.method, "positions": projection.positions,
            "axes": [[_plain(weight) for weight in axis] for axis in projection.axes],
            "citizens": [{"year": year, "xy": [_xy(p) for p in xy]} for year, xy in sorted(projection.citizen_xy.items())],
        },
        "parties": [party for party in (_party(projection, pid, platform) for pid, platform in loaded.parties) if party],
        "citizen_parties": [row.get("party_affiliation") for row in census_zero],
    }


def _story(loaded: LoadedRun) -> dict[str, Any]:
    """The terms, the institutional timeline and the curves."""
    macro = loaded.macro
    return {
        "terms": [_plain(term) for term in macro.terms],
        "timeline": [{**_plain(entry), "details": dict(entry.details)} for entry in macro.timeline],
        "standings": [{**_plain(s), "acts": list(s.acts)} for s in macro.standings],
        "elections": [_plain(e) for e in macro.elections],
        "legislative": [
            {"tick": p.tick, "blank_rate": p.blank_rate, "seats": [{"party_id": k, "seats": v} for k, v in sorted(p.seats.items())]}
            for p in macro.legislative
        ],
    }


def _overview(entry: CatalogEntry, loaded: LoadedRun) -> dict[str, Any]:
    frames = loaded.frames
    return {
        "key": entry.key, "label": entry.label, "run_id": frames.run_id, "population": frames.population,
        "ticks_per_year": frames.ticks_per_year, "last_tick": len(frames.frames) - 1,
        "last_checkpoint_tick": frames.last_checkpoint_tick, "vote_coverage": frames.vote_coverage,
        "unknown_event_types": list(frames.unknown_event_types),
        **_map(loaded), **_story(loaded),
        "motifs": [{"code": code, "label": label} for code, label in motif_labels().items()],
    }


def polity_run_overview(context: ExplorerContext, run_key: str) -> Body:
    try:
        entry, run = _load(context, run_key)
    except _Refused as refused:
        return refused.body
    return _overview(entry, run), 200


def _frame(frame: TickFrame) -> dict[str, Any]:
    president = frame.president
    return {
        "tick": frame.tick, "partial": frame.partial, "status": list(frame.status), "chamber": list(frame.chamber),
        "act": list(frame.act), "vote": list(frame.vote), "candidacy": list(frame.candidacy),
        "president": None if president is None else {
            "citizen_id": president.citizen_id, "xy": _xy(president.xy),
            "pledged_xy": _xy(president.pledged_xy) if president.pledged_xy is not None else None,
            "legitimacy": president.legitimacy, "ecart": president.ecart, "mandate_strength": president.mandate_strength,
            "lame_duck": president.lame_duck,
        },
    }


def polity_run_frames(context: ExplorerContext, run_key: str, from_tick: int, to_tick: int | None) -> Body:
    try:
        entry, run = _load(context, run_key)
    except _Refused as refused:
        return refused.body
    last = len(run.frames.frames) - 1
    end = min(from_tick + MAX_FRAME_SPAN - 1, last) if to_tick is None else to_tick
    if from_tick > last:
        return {"error": f"from_tick {from_tick} is past the run's last tick, {last}"}, 400
    if end < from_tick:
        return {"error": "to_tick is before from_tick"}, 400
    if end - from_tick + 1 > MAX_FRAME_SPAN:
        return {"error": f"at most {MAX_FRAME_SPAN} ticks per request"}, 400
    end = min(end, last)
    return {"key": entry.key, "from_tick": from_tick, "to_tick": end,
            "frames": [_frame(f) for f in run.frames.frames[from_tick:end + 1]]}, 200


def polity_citizen(context: ExplorerContext, run_key: str, citizen_id: int) -> Body:
    try:
        entry, run = _load(context, run_key)
    except _Refused as refused:
        return refused.body
    if citizen_id >= run.frames.population:
        return {"error": "citizen not found"}, 404
    biography = run.biography(citizen_id)
    return {
        "key": entry.key, "citizen_id": citizen_id,
        "sections": {section: [{**_plain(e), "details": dict(e.details)} for e in entries] for section, entries in biography.sections.items()},
        "received": [_plain(r) for r in biography.received],
        "census": [_plain(c) for c in biography.census],
    }, 200
