"""Running the deterministic twin for Stage 4's calibrations (scripts/calibrate_*.py).

The twin is run_polity_flagship.py's full-mechanism config at population 100 and 30 chamber
seats, on the deterministic engine, each run in a throwaway directory. `recording` wraps a
production function of the engine module for the length of a run, handing every call's
arguments and result to a recorder and returning the result unchanged.
"""
from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import api.domain.polity.run_polity_simulation as engine  # noqa: E402
from api.domain.polity.config import PolityConfig  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

SEEDS = tuple(range(1, 11))
POPULATION = 100
SEATS = 30


def twin_config(seed: int, years: int) -> PolityConfig:
    config = _flagship_config(engine="deterministic", years=years, population=POPULATION, seats=SEATS, seed=seed,
                              output_dir=Path("unused"), max_batch_replays=2, provider=None, workers=1)
    return dataclasses.replace(config, journal=dataclasses.replace(config.journal, index_after_run=False))


@contextmanager
def recording(name: str, recorder: Callable[[tuple[Any, ...], dict[str, Any], Any], None]) -> Iterator[None]:
    real = getattr(engine, name)

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = real(*args, **kwargs)
        recorder(args, kwargs, result)
        return result

    setattr(engine, name, wrapper)
    try:
        yield
    finally:
        setattr(engine, name, real)


@contextmanager
def observing(observer: Callable[[Any, Any], None]) -> Iterator[None]:
    """Append a last phase to every tick that hands its context and state to `observer`."""
    real = engine.TICK_PHASES
    engine.TICK_PHASES = (*real, observer)
    try:
        yield
    finally:
        engine.TICK_PHASES = real


def run_twin(config: PolityConfig) -> list[dict[str, Any]]:
    """Run `config` to the end and return its journal's events."""
    return run_twin_with_snapshots(config)[0]


def run_twin_with_snapshots(config: PolityConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run `config` to the end and return its journal's events and its yearly snapshot rows."""
    with tempfile.TemporaryDirectory() as tmp:
        config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=tmp))
        journal = engine.run_simulation(config, run_id="twin")

        def read(path: Path) -> list[dict[str, Any]]:
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        return read(journal), read(journal.parent / "snapshots.jsonl")
