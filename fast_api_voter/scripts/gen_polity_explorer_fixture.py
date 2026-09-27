"""Regenerates the run explorer's committed fixture run (run explorer B3): a short run of
the golden LLM scenario, driven by a fake model that votes and presses like a population,
kept under polity_fixtures/runs/explorer-fixture for the API and the Vote App's page tests.

Kept: the journal, the census, the final checkpoint, and the config, progress and
metadata files with every machine- or time-dependent field left out (paths, git, GPU,
timings). Dropped: the DuckDB index and the model call log. MANIFEST.json records each
kept file's sha256 and the config hash; test_polity_explorer_fixture.py checks both, and
that the run still replays. The run is not regenerated in CI: its floats can differ in the
last bits across BLAS builds, so a regeneration is a reviewed change like any other.

Usage (from fast_api_voter/):
    python scripts/gen_polity_explorer_fixture.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.checkpoint import config_hash  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.tests.polity_explorer_fixtures import (  # noqa: E402
    FIXTURE_MANIFEST,
    FIXTURE_ROOT,
    FIXTURE_RUN_ID,
    FixtureLlmClient,
    file_digests,
    fixture_config,
    replay_mismatches,
)

COPIED = ("events.jsonl", "snapshots.jsonl", "checkpoint.json")
STABLE_METADATA = (
    "run_id", "engine", "llm_enabled", "llm_provider", "llm_model", "seed", "population_size", "duration_years",
    "ticks_per_year", "total_ticks", "assembly_seats", "sortition_seats", "config_hash",
)
STABLE_PROGRESS = (
    "run_id", "tick", "total_ticks", "simulated_year", "decisions_by_type", "decisions_total", "retry_count",
    "fallback_count", "fallback_by_type", "last_checkpoint_tick", "tick_in_progress",
)


def _subset(path: Path, keys: tuple[str, ...]) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key: data[key] for key in keys if key in data}


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def generate(out_root: Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        config = fixture_config(Path(tmp))
        source = run_simulation(config, run_id=FIXTURE_RUN_ID, llm_client=FixtureLlmClient()).parent
        target = out_root / FIXTURE_RUN_ID
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True)
        for name in COPIED:
            shutil.copy(source / name, target / name)
        run_config = json.loads((source / "config.json").read_text(encoding="utf-8"))
        run_config["journal"]["output_dir"] = "polity_fixtures/runs"
        _write_json(target / "config.json", run_config)
        _write_json(target / "progress.json", _subset(source / "progress.json", STABLE_PROGRESS))
        _write_json(target / "run_metadata.json", _subset(source / "run_metadata.json", STABLE_METADATA))
        for path in target.iterdir():
            if tmp in path.read_text(encoding="utf-8"):
                raise RuntimeError(f"{path.name} still holds the temporary run directory's path")
    mismatches = replay_mismatches(target)
    if mismatches:
        raise RuntimeError(f"the fixture run does not replay: {mismatches[:3]}")
    _write_json(target / FIXTURE_MANIFEST, {"run_id": FIXTURE_RUN_ID, "config_hash": config_hash(config), "files": file_digests(target)})
    return target


def main() -> int:
    target = generate(FIXTURE_ROOT)
    size = sum(path.stat().st_size for path in target.iterdir())
    print(f"wrote {target} ({size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
