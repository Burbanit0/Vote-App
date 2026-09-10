"""
api.domain.polity.journal — append-only event log (Lot 7, design doc
§16.1-16.3).

Write-only in v0: "le journal est écrit append-only, mais n'est ni relu, ni
indexé, ni interrogé pendant le run" (§16.1). Replaying it into a queryable
store is indexer.py's job — not part of the v0 lot breakdown, and not
needed to validate the mechanical skeleton.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, TextIO

from api.domain.polity.config import JournalConfig


@dataclasses.dataclass(frozen=True)
class JournalEvent:
    run_id: str
    event_id: int
    tick: int
    event_type: str
    payload: dict[str, Any]
    citizen_id: int | None = None
    motif: str | None = None
    rationale: str | None = None
    # §3.7: the compression codebook is a v2+ concept — present and empty
    # in v0 so the schema doesn't need a migration once it exists.
    codebook_version: str = ""


class Journal:
    """One JSONL file per run. Every `write()` call assigns the next
    sequential event_id (D8: order is guaranteed by call order, not by a
    later sort) and is flushed to the OS immediately, so a process killed
    at any point leaves every already-written line complete and parseable
    — a crash can only ever truncate the *next* write, never corrupt one
    that already returned.

    `start_event_id` (Phase 3, plan-flagship-30y-run.md): a resumed run's
    journal must NOT restart numbering at 0 -- the file already on disk
    (truncated to the checkpoint's own `next_event_id` by
    `truncate_journal`, below, before this constructor ever runs) has real
    events occupying ids `0..start_event_id-1`. Every existing call site
    passes neither this nor anything that would change (the default keeps
    every pre-Phase-3 run starting at 0, unchanged)."""

    def __init__(self, path: Path, run_id: str, *, start_event_id: int = 0):
        self._run_id = run_id
        self._next_event_id = start_event_id
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file: TextIO = path.open("a", encoding="utf-8")

    @property
    def next_event_id(self) -> int:
        """The event_id the NEXT `write()` call will assign -- equivalently,
        how many events this journal has written so far (from this
        instance's own start_event_id, or 0 for a fresh run). A checkpoint
        taken right after this journal's last write for the completed tick
        should record this value: resuming from that checkpoint constructs
        a new Journal with `start_event_id` set to it, so numbering
        continues exactly where the crashed run left off."""
        return self._next_event_id

    @classmethod
    def from_config(cls, config: JournalConfig, run_id: str, *, start_event_id: int = 0) -> Journal:
        return cls(Path(config.output_dir) / run_id / "events.jsonl", run_id, start_event_id=start_event_id)

    def write(
        self,
        tick: int,
        event_type: str,
        payload: dict[str, Any],
        *,
        citizen_id: int | None = None,
        motif: str | None = None,
        rationale: str | None = None,
        codebook_version: str = "",
    ) -> int:
        event = JournalEvent(
            run_id=self._run_id,
            event_id=self._next_event_id,
            tick=tick,
            event_type=event_type,
            payload=payload,
            citizen_id=citizen_id,
            motif=motif,
            rationale=rationale,
            codebook_version=codebook_version,
        )
        # sort_keys: byte-for-byte reproducibility must not depend on
        # `payload`'s own construction order across two otherwise-identical
        # runs (Lot 8's end-to-end test compares journals byte for byte).
        line = json.dumps(dataclasses.asdict(event), sort_keys=True)
        self._file.write(line + "\n")
        self._file.flush()
        self._next_event_id += 1
        return event.event_id

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> Journal:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def truncate_journal(path: Path, keep_events: int) -> None:
    """Phase 3 (plan-flagship-30y-run.md): discards every event AFTER the
    last one the checkpoint being resumed from actually accounts for.

    A crash between "finish tick T, save its checkpoint" and "finish tick
    T+1" can leave `events.jsonl` holding some of tick T+1's own events,
    already flushed (`write()`'s own contract: every completed write is
    durable) but never checkpointed. Resuming without discarding them would
    re-run tick T+1 from its restored tick-T state and re-journal its
    events a SECOND time, appended after the stale ones -- not merely
    duplicated ids, but a journal that no longer matches what an
    uninterrupted run would have produced, the exact property Phase 3's own
    gate checks byte-for-byte.

    Called BEFORE `Journal(...)`/`Journal.from_config(...)` ever opens the
    resumed run's file in append mode -- truncation has to happen while the
    file is still closed (or at least not held open by a Journal that
    assumes it owns every byte from its own `start_event_id` onward).

    `keep_events` is the checkpoint's own `next_event_id` (the journal's
    `next_event_id` property at checkpoint time) -- lines are 1:1 with
    events (`write()` emits exactly one line per call, D8's own ordering
    guarantee), so "keep the first N lines" and "keep the first N events"
    are the same operation. A no-op if the file already has exactly
    `keep_events` lines or fewer (the clean-shutdown case, or a checkpoint
    somehow taken after the file was already at that length) -- never
    extends a short file."""
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) <= keep_events:
        return
    path.write_text("".join(lines[:keep_events]), encoding="utf-8")
