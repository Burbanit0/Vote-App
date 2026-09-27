"""Stage 4 on the LLM path: the pilot that sizes it before anything is pre-registered.

The owner chose to calibrate S4.1-S4.3 on the LLM path rather than on the deterministic twin
(D9, 2026-09-16). A twin run takes 0.2 s; an LLM run takes tens of minutes, so the calibration
has to be designed around a measured cost, not an estimate. This measures it, and checks the one
shortcut the design rests on.

`run` -- one recorded LLM run in the calibrations' own shape: population 100, 30 chamber seats,
seed 1, 8 years, the flagship's full-mechanism config, 12 workers (`llm.reproducibility: relaxed`,
S2.1). Legislation is on at one setting with `policy_retrospection` 0. It writes the call log the
replay needs, and records its wall-clock time.

`replay` -- replays that call log with a *different* legislation setting, on CPU. At weight 0 a
legislation setting changes no request the model is asked (checked on the fake client: two
different legislative histories, 455 byte-identical requests), so one recorded run per seed
could serve all nine of S4.2's (interval, step) settings for L1-L3. The replay client raises on
any request it never recorded, so this either confirms the shortcut on real model output or
refutes it.

Usage (from fast_api_voter/; `run` needs the vLLM server, `replay` does not):
    python scripts/stage4_llm_pilot.py run
    python scripts/stage4_llm_pilot.py replay
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import PolityConfig, validate_config  # noqa: E402
from api.domain.polity.llm_replay import ReplayClient  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from run_polity_flagship import _flagship_config, _write_digest_safely  # noqa: E402

RUNS = Path(__file__).resolve().parent / "stage4_llm_runs"
RUN_ID = "pilot-8y-p100-seed1"
YEARS, POPULATION, SEATS, SEED, WORKERS = 8, 100, 30, 1, 12
RECORDED = {"bill_interval_ticks": 4, "max_bill_step": 0.05}
REPLAYED = {"bill_interval_ticks": 1, "max_bill_step": 0.20}


def pilot_config(output_dir: Path, legislation: dict[str, float]) -> PolityConfig:
    config = _flagship_config(
        engine="llm", years=YEARS, population=POPULATION, seats=SEATS, seed=SEED,
        output_dir=output_dir, max_batch_replays=2, provider=None, workers=WORKERS,
        reproducibility="relaxed",
    )
    config = dataclasses.replace(
        config,
        legislation=dataclasses.replace(config.legislation, enabled=True, **legislation),
        vote=dataclasses.replace(config.vote, policy_retrospection=0.0),
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
    )
    validate_config(config)
    return config


def run() -> int:
    run_dir = RUNS / RUN_ID
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} exists; the journal appends, so a second run would concatenate two")
    run_dir.mkdir(parents=True)
    config = pilot_config(run_dir / "run", RECORDED)
    (run_dir / "config.json").write_text(json.dumps(dataclasses.asdict(config), indent=2, default=str), encoding="utf-8")
    print(f"[pilot] {RUN_ID}: {YEARS}y x {POPULATION}, {SEATS} seats, {WORKERS} workers, legislation {RECORDED}",
          flush=True)
    start = time.monotonic()
    journal = Path(config.journal.output_dir) / RUN_ID / "events.jsonl"
    try:
        journal = run_simulation(config, run_id=RUN_ID)
    except BaseException as exc:
        _write_digest_safely(journal, config, run_id=RUN_ID, outcome="crashed", resume=False,
                             elapsed_seconds=time.monotonic() - start, error=exc)
        raise
    elapsed = time.monotonic() - start
    _write_digest_safely(journal, config, run_id=RUN_ID, outcome="completed", resume=False,
                         elapsed_seconds=elapsed, error=None)
    (run_dir / "pilot_timing.json").write_text(json.dumps({"elapsed_seconds": elapsed, "workers": WORKERS}) + "\n")
    print(f"[pilot] completed in {elapsed / 60:.1f} min", flush=True)
    return 0


def replay() -> int:
    recorded_run = RUNS / RUN_ID / "run" / RUN_ID
    client = ReplayClient.from_run_dir(recorded_run)
    with tempfile.TemporaryDirectory() as work:
        config = pilot_config(Path(work), REPLAYED)
        start = time.monotonic()
        events_path = run_simulation(config, run_id=RUN_ID, llm_client=client)
        events = [json.loads(line) for line in Path(events_path).read_text().splitlines() if line.strip()]
    bills = sum(1 for e in events if e["event_type"] == "bill_proposed")
    enacted = sum(1 for e in events if e["event_type"] == "bill_enacted")
    recorded_bills = sum(1 for line in (recorded_run / "events.jsonl").read_text().splitlines()
                         if line.strip() and json.loads(line)["event_type"] == "bill_proposed")
    print(f"[replay] legislation {REPLAYED} over the call log recorded at {RECORDED}")
    print(f"[replay] {client.served} recorded calls served, {client.unserved} never asked for, "
          f"{time.monotonic() - start:.0f} s on CPU")
    print(f"[replay] bills proposed: {recorded_bills} recorded run, {bills} replayed ({enacted} enacted)")
    verdict = "HOLDS" if client.unserved == 0 else "DIVERGED"
    print(f"[replay] the record-and-replay shortcut {verdict}")
    return 0 if client.unserved == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("mode", choices=["run", "replay"])
    raise SystemExit(run() if parser.parse_args().mode == "run" else replay())
