"""
scripts/check_pressure_small_run.py

A genuinely small, real run_simulation() pass against the live vLLM
server, to see the Phase E calibration fix (polity-decision-contracts.md)
behave inside an actual simulation -- not an isolated decide_pressure_
actions call (check_pressure_shipped_wiring.py) and not a hand-built
single tick (test_pressure_action_wiring_against_the_real_client_in_a_
live_tick) -- the real tick loop, real elections, real accountability
phase, over several ticks.

Same known-working recipe as test_a_short_live_run_produces_a_valid_
journal (candidacy.ambition_threshold=0.1, duration_years=4 -- both
needed for a real election to actually occur in a short run), with
run.population_size cut from the shipped 100 down to 20 to keep this
fast: at batch size 1 (_PRESSURE_CALIBRATED_CHUNK_SIZE), pressure_action
is one real HTTP call per consulted citizen per tick, so population size
is now the dominant cost lever, not chunk count.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_pressure_small_run.py
"""
from __future__ import annotations

import collections
import dataclasses
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402


def main() -> int:
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.1))
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, population_size=20, duration_years=4))
    # pressure_action's own "awaken -> consult" gate (§7bis.9d: a sampling GATE, never a decision)
    # is OFF by default in the shipped yaml -- config.awakening.enabled=false means nobody is ever
    # consulted at all, and the accountability phase's own docstring notes pressure levers require
    # legitimacy.enabled too. Both are false in the bare shipped config (features stay off until a
    # given run's own profile turns them on -- confirmed the first run of this script produced ZERO
    # pressure_action events for exactly this reason, elections notwithstanding). The real
    # flagship run enables both (it is the only way check_pressure_batch_size_cost_results.md's own
    # "137 real pressure_action decisions/tick" anchor could ever have been measured) -- mirrored
    # here, same as test_pressure_action_wiring_against_the_real_client_in_a_live_tick already does.
    # pressure_menu.electoral_only stays at its shipped True: that closed-menu regime is what
    # Phase E actually calibrated and shipped for, not an opened-up menu.
    config = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))
    config = dataclasses.replace(config, awakening=dataclasses.replace(config.awakening, enabled=True))

    out_dir = Path("/tmp/check_pressure_small_run")
    out_dir.mkdir(parents=True, exist_ok=True)
    config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(out_dir)))

    print(f"provider={config.llm.provider} base_url={config.llm.base_url} "
          f"population_size={config.run.population_size} duration_years={config.run.duration_years}")

    start = time.perf_counter()
    journal_path = run_simulation(config, run_id="pressure-small-run")
    elapsed = time.perf_counter() - start
    print(f"\nrun completed in {elapsed:.1f}s -> {journal_path}")

    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    by_type = collections.Counter(e["event_type"] for e in events)
    print(f"\ntotal events: {len(events)}")
    for event_type, n in by_type.most_common():
        print(f"  {event_type}: {n}")

    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    print(f"\npressure_action events: {len(pressure_events)}")
    if not pressure_events:
        print("no pressure_action events fired -- no election/officeholder occurred in this short a run")
        return 0

    act_hist = collections.Counter(e["payload"]["act"] for e in pressure_events)
    print(f"act histogram: {dict(act_hist)}")

    # self_gap is journaled per decision (PressureContext.to_payload, only present
    # when an LLM decision was actually made, not the deterministic fallback).
    with_ctx = [e for e in pressure_events if "ctx" in e["payload"]]
    print(f"LLM-decided (carries ctx.self_gap): {len(with_ctx)}/{len(pressure_events)}")
    if with_ctx:
        by_act: dict[int, list[float]] = collections.defaultdict(list)
        for e in with_ctx:
            by_act[e["payload"]["act"]].append(e["payload"]["ctx"]["self_gap"])
        print("mean self_gap by chosen act (higher act=4 [wait] vs act=0 [nothing] should differ if the fix is working):")
        for act, gaps in sorted(by_act.items()):
            print(f"  act={act}: n={len(gaps)}, mean self_gap={sum(gaps) / len(gaps):.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
