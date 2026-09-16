"""Which runs the explorer can open, and each one loaded once.

Runs live under named roots (`POLITY_RUN_ROOTS`, "label=path" pairs separated by commas).
A run is known by a key derived from its root's label and its path inside that root, so
the same run has the same key on every machine that mounts it under the same label, and
no absolute path ever leaves the server. A run is listed when it has a journal, a config
and a census, and when every file the explorer would read from it resolves inside its
root and is no larger than the configured limit. A run holding a file that escapes its
root -- a symlink to somewhere else on the host -- is not listed at all, so no reader
downstream has to be careful.

A loaded run is cached by the modification time and size of every file its load reads, so
a run that is still being written is read again once any of them changes, and the first
readers of a cold run wait for one load rather than each making their own.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any
from weakref import WeakValueDictionary

from api.domain.polity.explorer_biography import Biography, build_biography
from api.domain.polity.explorer_paths import inside
from api.domain.polity.run_explorer import RunView
from api.domain.polity.run_frames import RunFrames, frames_for
from api.domain.polity.run_macro import RunMacro, build_macro
from api.domain.polity.run_registry import discover_runs, run_record

DEFAULT_RUN_ROOT = Path(__file__).resolve().parents[3] / "polity_fixtures" / "runs"
"""The committed fixture run's root, served under the label "fixture" when no roots are configured."""
RUN_KEY_PATTERN = re.compile(r"^[0-9a-f]{16}$")
_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_REQUIRED_FILES = ("events.jsonl", "config.json", "snapshots.jsonl")
_OPTIONAL_FILES = ("checkpoint.json", "progress.json", "run_metadata.json", "digest.json", "llm_calls_summary.json")
"""Read when present: the parties, the last checkpointed tick, and the registry row's provenance."""


class RunRootsError(ValueError):
    """A POLITY_RUN_ROOTS value that cannot be read."""


@dataclass(frozen=True)
class RunRoot:
    label: str
    path: Path


def parse_roots(spec: str) -> tuple[RunRoot, ...]:
    roots = []
    for entry in (part.strip() for part in spec.split(",")):
        if not entry:
            continue
        label, separator, path = entry.partition("=")
        if not separator or not _LABEL_PATTERN.match(label) or not path:
            raise RunRootsError(f"run root {entry!r} is not label=path (label: letters, digits, _ or -)")
        roots.append(RunRoot(label=label, path=Path(path)))
    if len({root.label for root in roots}) != len(roots):
        raise RunRootsError("run root labels must be unique")
    return tuple(roots)


def run_key(label: str, relative_path: str) -> str:
    return hashlib.sha256(f"{label}/{relative_path}".encode()).hexdigest()[:16]


@dataclass(frozen=True)
class CatalogEntry:
    key: str
    label: str
    relative_path: str
    run_dir: Path
    record: dict[str, Any]


def _readable(run_dir: Path, root: Path, name: str, max_bytes: int) -> bool:
    """A file the explorer reads: absent is fine, outside the root or oversized is not.

    Every file is capped, not just the journal: they are all read whole into memory
    (`snapshots.jsonl` of a p500 run is the second large one).
    """
    path = run_dir / name
    if not path.exists():  # a dangling symlink reads as absent too, and is read as {}
        return True
    return path.is_file() and inside(path, root) and path.stat().st_size <= max_bytes


def _explorable_dir(run_dir: Path, root: Path, max_journal_bytes: int) -> bool:
    if not inside(run_dir, root) or not all((run_dir / name).is_file() for name in _REQUIRED_FILES):
        return False
    return all(_readable(run_dir, root, name, max_journal_bytes) for name in _REQUIRED_FILES + _OPTIONAL_FILES)


def _explorable(roots: Sequence[RunRoot], max_journal_bytes: int) -> list[tuple[str, RunRoot, str, Path]]:
    """(key, root, relative path, run directory) for every explorable run, records unread."""
    found = []
    for root in roots:
        for run_dir in discover_runs([root.path]):
            if _explorable_dir(run_dir, root.path, max_journal_bytes):
                relative = run_dir.relative_to(root.path).as_posix()
                found.append((run_key(root.label, relative), root, relative, run_dir))
    return found


def _entry(key: str, root: RunRoot, relative: str, run_dir: Path) -> CatalogEntry:
    return CatalogEntry(key=key, label=root.label, relative_path=relative, run_dir=run_dir,
                        record=run_record(run_dir, confine=root.path))


def list_runs(roots: Sequence[RunRoot], max_journal_bytes: int) -> list[CatalogEntry]:
    return [_entry(*found) for found in _explorable(roots, max_journal_bytes)]


def find_run(roots: Sequence[RunRoot], key: str, max_journal_bytes: int) -> CatalogEntry | None:
    if not RUN_KEY_PATTERN.match(key):
        return None
    return next((_entry(*found) for found in _explorable(roots, max_journal_bytes) if found[0] == key), None)


@dataclass(frozen=True)
class LoadedRun:
    view: RunView
    frames: RunFrames
    macro: RunMacro
    parties: tuple[tuple[int, tuple[float, ...]], ...]
    """(party_id, platform) from the final checkpoint; platforms never move during a run."""

    def biography(self, citizen_id: int) -> Biography:
        return build_biography(self.view, citizen_id)


def _parties(run_dir: Path) -> tuple[tuple[int, tuple[float, ...]], ...]:
    """The parties of a run's final checkpoint, a malformed entry dropped rather than
    raised: a run whose checkpoint is torn or from another engine version still opens,
    without its party markers."""
    try:
        checkpoint = json.loads((run_dir / "checkpoint.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("parties"), list):
        return ()
    found = []
    for party in checkpoint["parties"]:
        if not isinstance(party, dict):
            continue
        try:
            found.append((int(party["party_id"]), tuple(float(x) for x in party["platform"])))
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(found)


def load_run(run_dir: Path) -> LoadedRun:
    view = RunView.load(run_dir)
    frames = frames_for(run_dir, view.events, view.snapshots)
    return LoadedRun(view=view, frames=frames, macro=build_macro(view.events, frames.population, view.last_tick),
                     parties=_parties(run_dir))


_LOADED_FILES = ("events.jsonl", "snapshots.jsonl", "config.json", "checkpoint.json", "progress.json")
"""The files `load_run` reads. A cached run is stale when any of them changes."""

Stamp = tuple[tuple[int, int] | None, ...]


def _stamp(run_dir: Path) -> Stamp:
    """(modification time, size) per file the load reads, None for one that is absent."""
    stamps: list[tuple[int, int] | None] = []
    for name in _LOADED_FILES:
        try:
            stat = (run_dir / name).stat()
        except OSError:
            stamps.append(None)
        else:
            stamps.append((stat.st_mtime_ns, stat.st_size))
    return tuple(stamps)


class RunCache:
    """The last `capacity` runs opened, each reloaded when any file it was read from changes."""

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._runs: OrderedDict[Path, tuple[Stamp, LoadedRun]] = OrderedDict()
        self._lock = Lock()
        # One lock per run being loaded, so the four requests a page load makes wait for
        # one load instead of each building its own copy (a p500 run is ~6x its journal
        # resident). Weak values: the lock goes away once no thread holds it.
        self._loads: WeakValueDictionary[Path, Lock] = WeakValueDictionary()

    def get(self, run_dir: Path) -> LoadedRun:
        stamp = _stamp(run_dir)
        cached = self._cached(run_dir, stamp)
        if cached is not None:
            return cached
        with self._load_lock(run_dir):
            cached = self._cached(run_dir, stamp)  # another thread may have loaded it while we waited
            if cached is not None:
                return cached
            loaded = load_run(run_dir)
            with self._lock:
                self._runs[run_dir] = (stamp, loaded)
                self._runs.move_to_end(run_dir)
                while len(self._runs) > self._capacity:
                    self._runs.popitem(last=False)
            return loaded

    def _cached(self, run_dir: Path, stamp: Stamp) -> LoadedRun | None:
        with self._lock:
            cached = self._runs.get(run_dir)
            if cached is None or cached[0] != stamp:
                return None
            self._runs.move_to_end(run_dir)
            return cached[1]

    def _load_lock(self, run_dir: Path) -> Lock:
        with self._lock:
            existing = self._loads.get(run_dir)
            if existing is not None:
                return existing
            created = Lock()
            self._loads[run_dir] = created
            return created

    def __len__(self) -> int:
        return len(self._runs)

