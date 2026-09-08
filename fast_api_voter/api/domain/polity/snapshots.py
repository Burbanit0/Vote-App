"""
api.domain.polity.snapshots — per-simulated-year citizen state (Phase 6,
plan-flagship-30y-run.md, design doc §16.4).

Once per simulated year, snapshots every citizen's own state -- the only way
§14.1 (micro force graph) and §14.2 (méso 2D projection, animated over 30
years) can be built without replaying the ENTIRE journal to reconstruct a
citizen's own trajectory at each point in time. Settles §14.6's own open
question ("snapshots generated during the run or in post-processing?") as
BOTH, deliberately: a snapshot taken during the run is cheap insurance
against discovering, post-hoc, that the data needed for a specific frame was
never captured -- on a run too expensive (days of GPU) to simply re-run.

Written as a plain, append-only JSONL file (`snapshots.jsonl`, beside
`events.jsonl`/`checkpoint.json`/`progress.json` in the run's own directory)
-- the same register as the journal itself, not a live DuckDB table:
`compaction.compact_run`'s own precedent (§16.1's "the hot regime never
reads, indexes, or queries" rule) is that rich, queryable formats are a
strictly POST-run concern. `journal.truncate_journal` is reused as-is for
resume (a snapshot row is just another JSONL line; that function never
assumed anything about the journal's own event schema)."""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from api.domain.polity.citizen import Citizen


def is_snapshot_tick(tick: int, ticks_per_year: int) -> bool:
    """Once per simulated year, at the START of the year (tick 0,
    ticks_per_year, 2*ticks_per_year, ...) -- BEFORE that tick's own phases
    run, not after. Two consequences of that choice, both deliberate:

    1. The tick-0 snapshot captures the TRUE initial population -- pre-
       generation-population, pre-any-simulated-event -- a genuine "year 0
       baseline" a post-run analysis can compare every later year against,
       not a population already one tick's worth of decisions removed from
       its own starting state.
    2. `simulated_year = tick // ticks_per_year` lines up with `progress.py`'s
       own `simulated_year` field (`tick / ticks_per_year`) at the exact tick
       where they're both computed -- a `progress.json` read at a snapshot
       tick and the snapshot itself agree on which year they're describing."""
    return tick % ticks_per_year == 0


def expected_snapshot_rows(tick: int, ticks_per_year: int, population_size: int) -> int:
    """How many snapshot rows SHOULD exist in `snapshots.jsonl` once every
    tick up to and including `tick` has been fully processed -- a pure
    function of (tick, ticks_per_year, population_size), deliberately never
    persisted in the checkpoint itself (same "don't snapshot what's already
    derivable" discipline `checkpoint.py`'s own module docstring uses for
    the social graph). Needed on resume: a crash on a tick that both (a) is
    a snapshot tick and (b) never finished leaves a premature snapshot
    write on disk that was never checkpointed -- `expected_snapshot_rows`,
    evaluated at the CHECKPOINT's own last-completed tick (never the
    crashed one), gives `journal.truncate_journal` the exact line count to
    discard it back to before that tick restarts from scratch."""
    years_reached = tick // ticks_per_year + 1
    return years_reached * population_size


def _citizen_snapshot(citizen: Citizen, *, year: int, tick: int) -> dict[str, Any]:
    return {
        "year": year,
        "tick": tick,
        "citizen_id": citizen.citizen_id,
        "issue_positions": list(citizen.issue_positions),
        "party_affiliation": citizen.party_affiliation,
        "role": citizen.role.value,
        "office": citizen.office.value,
        "event_salience": citizen.event_salience,
        # Holder-specific (v0 for a plain elector, only ever set once a
        # candidacy is declared -- see Citizen's own docstring): both null
        # for the common case, both present once a citizen has ever run.
        "pledged_platform": list(citizen.pledged_platform) if citizen.pledged_platform is not None else None,
        "revealed_position": list(citizen.revealed_position) if citizen.revealed_position is not None else None,
    }


def write_snapshot(path: Path, citizens: Sequence[Citizen], *, tick: int, ticks_per_year: int) -> None:
    """Appends one row per citizen, called only when `is_snapshot_tick` is
    true. Plain append (`Journal.write`'s own register), not an atomic
    whole-file rewrite (`checkpoint`/`progress`'s own register): a torn
    last line from a mid-write crash is exactly like a partial tick's own
    journal entries -- never read mid-run, discarded and reproduced
    identically by `expected_snapshot_rows`-based truncation on resume, so
    it is not a live correctness risk the way a torn checkpoint/progress
    file would be.

    `sort_keys=True` + compact separators, matching `Journal.write`'s own
    canonical serialization -- the same byte-for-byte reproducibility
    discipline this project holds `events.jsonl` to applies here: an
    uninterrupted run and a killed-and-resumed run must produce an
    identical `snapshots.jsonl`, not just an identical `events.jsonl`."""
    year = tick // ticks_per_year
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for citizen in citizens:
            line = json.dumps(_citizen_snapshot(citizen, year=year, tick=tick), sort_keys=True, separators=(",", ":"))
            handle.write(line + "\n")
