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
    that already returned."""

    def __init__(self, path: Path, run_id: str):
        self._run_id = run_id
        self._next_event_id = 0
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file: TextIO = path.open("a", encoding="utf-8")

    @classmethod
    def from_config(cls, config: JournalConfig, run_id: str) -> Journal:
        return cls(Path(config.output_dir) / run_id / "events.jsonl", run_id)

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
