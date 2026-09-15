"""Which runs the explorer can open, and each one loaded once.

Runs live under named roots (`POLITY_RUN_ROOTS`, "label=path" pairs separated by commas).
A run is known by a key derived from its root's label and its path inside that root, so
the same run has the same key on every machine that mounts it under the same label, and
no absolute path ever leaves the server. A run is listed when it has a journal no larger
than the configured limit, a config and a census, and every file it is read from resolves
inside its root: a symlink out of the root is not followed.

A loaded run is cached by its journal's modification time and size, so a run that is
still being written is read again once it changes.
"""
from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from api.domain.polity.explorer_biography import Biography, build_biography
from api.domain.polity.run_explorer import RunView
from api.domain.polity.run_frames import RunFrames, frames_for
from api.domain.polity.run_macro import RunMacro, build_macro
from api.domain.polity.run_registry import discover_runs, run_record

RUN_KEY_PATTERN = re.compile(r"^[0-9a-f]{16}$")
_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_REQUIRED_FILES = ("events.jsonl", "config.json", "snapshots.jsonl")


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


def _inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def _explorable_dir(run_dir: Path, root: Path, max_journal_bytes: int) -> bool:
    files = [run_dir / name for name in _REQUIRED_FILES]
    if not all(f.is_file() and _inside(f, root) for f in files) or not _inside(run_dir, root):
        return False
    return (run_dir / "events.jsonl").stat().st_size <= max_journal_bytes


def list_runs(roots: Sequence[RunRoot], max_journal_bytes: int) -> list[CatalogEntry]:
    entries = []
    for root in roots:
        for run_dir in discover_runs([root.path]):
            if not _explorable_dir(run_dir, root.path, max_journal_bytes):
                continue
            relative = run_dir.relative_to(root.path).as_posix()
            entries.append(CatalogEntry(key=run_key(root.label, relative), label=root.label, relative_path=relative,
                                        run_dir=run_dir, record=run_record(run_dir)))
    return entries


def find_run(roots: Sequence[RunRoot], key: str, max_journal_bytes: int) -> CatalogEntry | None:
    if not RUN_KEY_PATTERN.match(key):
        return None
    return next((entry for entry in list_runs(roots, max_journal_bytes) if entry.key == key), None)


@dataclass(frozen=True)
class LoadedRun:
    view: RunView
    frames: RunFrames
    macro: RunMacro

    def biography(self, citizen_id: int) -> Biography:
        return build_biography(self.view, citizen_id)


def load_run(run_dir: Path) -> LoadedRun:
    view = RunView.load(run_dir)
    frames = frames_for(run_dir, view.events, view.snapshots)
    return LoadedRun(view=view, frames=frames, macro=build_macro(view.events, frames.population, view.last_tick))


class RunCache:
    """The last `capacity` runs opened, each reloaded when its journal changes."""

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._runs: OrderedDict[Path, tuple[tuple[int, int], LoadedRun]] = OrderedDict()
        self._lock = Lock()

    def get(self, run_dir: Path) -> LoadedRun:
        stat = (run_dir / "events.jsonl").stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        with self._lock:
            cached = self._runs.get(run_dir)
            if cached is not None and cached[0] == stamp:
                self._runs.move_to_end(run_dir)
                return cached[1]
        loaded = load_run(run_dir)
        with self._lock:
            self._runs[run_dir] = (stamp, loaded)
            self._runs.move_to_end(run_dir)
            while len(self._runs) > self._capacity:
                self._runs.popitem(last=False)
        return loaded

    def __len__(self) -> int:
        return len(self._runs)

