"""
api.domain.polity.checkpoint — per-tick state snapshot for a resumable run
(Phase 3, plan-flagship-30y-run.md).

Exists because `run_simulation()`'s own tick loop holds every piece of live
state (citizens, parties, 4 RNG streams, `economy_x`, `pending_rerun`,
`mobilized_last_tick`) in local variables -- a crash at hour 60 of a
multi-day sequential run (Phase 2's own conclusion: the flagship runs
sequential, not concurrent) forfeits everything with no durability. This
module is the pure (de)serialization layer; `run_simulation()` itself owns
WHEN to call it (once per completed tick) and how to splice the restored
state back into its own loop.

**Deliberately NOT snapshotted, and why**: `graph` (the social-graph
structure) and `InstitutionalClock` are both pure functions of
`(config, population_size, seed)` with zero mid-run mutation --
`social_graph.py`'s own docstring: "generated once, population-structural
(evolving is TRANCHÉ rejected at config-parse time, so this never changes
mid-run)"; `InstitutionalClock.from_config` takes config alone, holds no
state. Regenerating either from the resumed config reproduces them exactly;
snapshotting them would be pure duplication with its own resync risk.

**`pending_rerun`** (v4 Lot 9's `PendingRerun`) is intentionally NOT this
module's own type -- `run_polity_simulation.py` owns that class, and
importing it here would be circular (that module needs to call INTO this
one). This module's own save/load functions take/return a plain
`dict[str, Any] | None` for it; the caller does the (three-field, trivial)
conversion.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.config import PolityConfig
from api.domain.polity.parties import Party


@dataclasses.dataclass(frozen=True)
class Checkpoint:
    """Everything `run_simulation()` needs to splice back into its own tick
    loop and continue from `tick + 1`. `tick` is the last FULLY COMPLETED
    tick -- every field here reflects state as it stood at that tick's end,
    before any of `tick + 1`'s own phases ran. `next_event_id` is the
    journal's own `Journal.next_event_id` at that same moment, i.e. exactly
    how many events `events.jsonl` should hold once truncated
    (`journal.truncate_journal`) before a resumed `Journal` reopens it."""

    run_id: str
    config_hash: str
    tick: int
    next_event_id: int
    citizens: list[Citizen]
    parties: list[Party]
    pending_rerun: dict[str, Any] | None
    economy_x: float
    mobilized_last_tick: Mapping[int, int]
    rupture_rng_state: dict[str, Any]
    events_rng_state: dict[str, Any]
    sortition_rng_state: dict[str, Any]


def config_hash(config: PolityConfig) -> str:
    """A resume must run against the SAME simulation rules it crashed under
    -- population_size, seed, every institutional parameter, all of it.
    Excludes `raw` (a duplicate view of everything else already hashed) and
    `journal.output_dir` (a filesystem path, not a simulation parameter --
    resuming into a relocated run directory is legitimate). Anything else
    differing between the crashed run's config and the resume attempt's own
    config is exactly the class of mistake this hash exists to catch loudly,
    at resume time, rather than silently producing a run that is neither the
    old config nor the new one."""
    payload = dataclasses.asdict(config)
    payload.pop("raw", None)
    payload["journal"].pop("output_dir", None)
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _citizen_to_dict(citizen: Citizen) -> dict[str, Any]:
    # `vars(citizen).copy()`, not `dataclasses.asdict(citizen)` -- measured
    # 303x faster (3.2ms vs 0.011ms per 100-citizen pass) at population 100,
    # and the difference is NOT negligible here: this runs every tick, and a
    # flagship run's own per-tick GPU cost (283-1069s+, Phase 0/Phase 2's own
    # measurements) makes a checkpoint's cost irrelevant there either way --
    # but the same code path also runs on every polity test that calls
    # run_simulation, many of them for 120 ticks at population ~100, where
    # asdict's cost was NOT irrelevant (measured: +86s across the polity
    # suite, 37s -> 123s, entirely attributable to this one call). `asdict`
    # is slow here because its generic recursive implementation deep-copies
    # every field defensively, work `Citizen` (a flat dataclass -- no
    # dataclass-typed fields to recurse into) never needed. `vars()` returns
    # the instance's own `__dict__` directly; `.copy()` is required before
    # this function mutates a key (`petition_signers`, the one field
    # `json.dumps` cannot encode natively) so the citizen's own live state
    # is never touched. `role`/`office` need no conversion at all -- both
    # are `str, Enum` subclasses, which `json.dumps` already encodes as
    # their plain string value with no help; explicitly calling `.value`
    # would be correct but is pure overhead this rewrite deliberately drops.
    data = vars(citizen).copy()
    data["petition_signers"] = sorted(citizen.petition_signers)
    return data


def _citizen_from_dict(data: dict[str, Any]) -> Citizen:
    data = dict(data)
    data["role"] = Role(data["role"])
    data["office"] = Office(data["office"])
    data["petition_signers"] = frozenset(data["petition_signers"])
    data["issue_positions"] = tuple(data["issue_positions"])
    data["issue_priorities"] = tuple(data["issue_priorities"])
    if data["pledged_platform"] is not None:
        data["pledged_platform"] = tuple(data["pledged_platform"])
    if data["revealed_position"] is not None:
        data["revealed_position"] = tuple(data["revealed_position"])
    if data["chamber_position"] is not None:
        data["chamber_position"] = tuple(data["chamber_position"])
    return Citizen(**data)


def _party_to_dict(party: Party) -> dict[str, Any]:
    return {"party_id": party.party_id, "platform": list(party.platform)}


def _party_from_dict(data: dict[str, Any]) -> Party:
    return Party(party_id=data["party_id"], platform=tuple(data["platform"]))


def save_checkpoint(
    path: Path,
    *,
    run_id: str,
    config: PolityConfig,
    tick: int,
    next_event_id: int,
    citizens: list[Citizen],
    parties: list[Party],
    pending_rerun: dict[str, Any] | None,
    economy_x: float,
    mobilized_last_tick: Mapping[int, int],
    rupture_rng: np.random.Generator,
    events_rng: np.random.Generator,
    sortition_rng: np.random.Generator,
) -> None:
    """Atomic write (temp file + `os.replace`, same discipline `run_
    polity_flagship.py`'s own convention docs elsewhere in this project use
    for progress files) -- a process killed mid-write must never leave a
    half-written, unparseable `checkpoint.json` that a later resume attempt
    would load as valid JSON's evil twin (a truncated file that happens to
    still parse, silently missing fields). `os.replace` is atomic on both
    POSIX and Windows for same-filesystem renames, which a `.tmp` sibling in
    the same directory always is.

    RNG state (`generator.bit_generator.state`) is a plain dict of Python
    ints -- `json` round-trips arbitrary-precision Python ints exactly, no
    truncation risk even for PCG64's 128-bit state words."""
    payload = {
        "run_id": run_id,
        "config_hash": config_hash(config),
        "tick": tick,
        "next_event_id": next_event_id,
        "citizens": [_citizen_to_dict(c) for c in citizens],
        "parties": [_party_to_dict(p) for p in parties],
        "pending_rerun": pending_rerun,
        "economy_x": economy_x,
        "mobilized_last_tick": {str(k): v for k, v in mobilized_last_tick.items()},
        "rupture_rng_state": rupture_rng.bit_generator.state,
        "events_rng_state": events_rng.bit_generator.state,
        "sortition_rng_state": sortition_rng.bit_generator.state,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(tmp_path, path)


def load_checkpoint(path: Path) -> Checkpoint:
    """Raises FileNotFoundError (via `Path.read_text`'s own default
    behavior) if `path` doesn't exist -- `run_simulation`'s own `resume=True`
    caller is expected to let that propagate rather than silently starting
    fresh, since a resume attempt with no checkpoint to resume from is a
    caller error, not a legitimate first-run case (that's `resume=False`)."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Checkpoint(
        run_id=payload["run_id"],
        config_hash=payload["config_hash"],
        tick=payload["tick"],
        next_event_id=payload["next_event_id"],
        citizens=[_citizen_from_dict(c) for c in payload["citizens"]],
        parties=[_party_from_dict(p) for p in payload["parties"]],
        pending_rerun=payload["pending_rerun"],
        economy_x=payload["economy_x"],
        mobilized_last_tick={int(k): v for k, v in payload["mobilized_last_tick"].items()},
        rupture_rng_state=payload["rupture_rng_state"],
        events_rng_state=payload["events_rng_state"],
        sortition_rng_state=payload["sortition_rng_state"],
    )


def restore_rng(state: dict[str, Any]) -> np.random.Generator:
    """The seed passed to `default_rng` here is thrown away the instant
    `bit_generator.state` is overwritten -- it exists only because
    `default_rng` requires *some* seed to construct a generator at all, not
    because it contributes anything to the restored stream's actual
    position. Restoring `state` (captured from the live generator's own
    `bit_generator.state`) reproduces the exact draw position the crashed
    run's stream was at, which a fresh `default_rng(original_seed)` would
    NOT -- that would restart the stream from its beginning, replaying
    draws the crashed run already consumed and diverging from here on."""
    rng = np.random.default_rng(0)
    rng.bit_generator.state = state
    return rng
