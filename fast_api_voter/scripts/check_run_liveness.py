#!/usr/bin/env python3
"""Answer one question honestly: is this polity run alive, or is it stuck?

WHY THIS EXISTS. On 2026-09-11 a healthy Stage 3 run was diagnosed as hung
and killed, discarding ~2h of GPU compute. Every symptom the diagnosis rested
on was normal for this workload:

  - 1.92s of CPU in 1h59      the process is ~100% blocked on a GPU server;
                              parsing a small JSON batch costs less than one
                              10ms jiffy. LOW CPU PROVES NOTHING HERE.
  - no journal write for ~2h  cast_votes decides the WHOLE population before
                              its caller journals anything -- ~167 sequential
                              calls at pop 500, about an hour of legitimate
                              silence -- and it was an election tick, 8-10x
                              an ordinary one.
  - an idle ESTABLISHED       httpx reuses ONE keep-alive connection for every
    socket opened 1h41 ago    request. SOCKET AGE IS NOT REQUEST AGE.
  - a stale progress.json ETA it is written once per COMPLETED tick, by design.

So this script refuses to answer from those. It reads the intra-tick heartbeat
(`last_llm_response_at`, written by ProgressTracker.record_llm_activity on
every completed LLM response) and, when it can, asks the inference server
whether it is actually working -- the check whose absence caused the incident.

Usage:
    python scripts/check_run_liveness.py <run-dir-or-progress.json> [--stale-after SECONDS]

Exit codes: 0 alive, 1 suspect (stale heartbeat), 2 cannot tell.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# A heartbeat older than this is worth LOOKING at -- it is not a verdict.
# Sized off the real worst case: a pop-500 election tick's slowest single
# decision is campaign_positioning (think=True, +8000 token allowance), and at
# the ~130-170 tok/s this GPU sustains a maximal generation is a couple of
# minutes. Ten minutes is several times that, so a heartbeat this old means
# no response has arrived for far longer than any one call should take.
_DEFAULT_STALE_AFTER_SECONDS = 600.0


def _resolve_progress_path(target: Path) -> Path:
    if target.is_file():
        return target
    direct = target / "progress.json"
    if direct.is_file():
        return direct
    matches = sorted(target.glob("run/*/progress.json")) or sorted(target.glob("*/progress.json"))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"no progress.json under {target}")
    raise SystemExit("several progress.json found; name one:\n  " + "\n  ".join(str(m) for m in matches))


def _server_activity(container: str, window: str = "3m") -> tuple[int | None, str]:
    """Completed chat completions the inference server logged in `window`.

    This is the check that was missing on 2026-09-11. A nonzero, advancing
    count means the run is fine NO MATTER how quiet its journal is. Returns
    (None, reason) when the server cannot be consulted -- never a guess."""
    try:
        proc = subprocess.run(
            ["docker", "logs", "--since", window, container],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except FileNotFoundError:
        return None, "docker not on PATH"
    except subprocess.TimeoutExpired:
        return None, "docker logs timed out"
    if proc.returncode != 0:
        return None, f"container {container!r} not readable"
    blob = proc.stdout + proc.stderr
    return blob.count("POST /v1/chat/completions"), f"last {window}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", type=Path, help="run directory or a progress.json")
    parser.add_argument("--stale-after", type=float, default=_DEFAULT_STALE_AFTER_SECONDS)
    parser.add_argument("--container", default="vllm-polity", help="inference server container to consult")
    args = parser.parse_args()

    path = _resolve_progress_path(args.target)
    progress: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    run_id = progress.get("run_id", "?")
    tick = progress.get("tick")
    in_progress = progress.get("tick_in_progress")
    total = progress.get("total_ticks")
    calls = progress.get("llm_calls_completed", 0)
    last_response_at = progress.get("last_llm_response_at")

    print(f"run          {run_id}")
    print(f"ticks        {tick}/{total} complete" + (f", tick {in_progress} in progress" if in_progress else ""))
    print(f"llm calls    {calls} completed this process")

    if last_response_at is None:
        print("heartbeat    absent")
        print()
        print("CANNOT TELL. No heartbeat in this file. Either the run predates the")
        print("intra-tick heartbeat (2026-09-11) or it has made no LLM call yet.")
        print("Ask the server directly before concluding anything:")
        print(f"  docker logs --since 5m {args.container} | grep -c 'POST /v1/chat/completions'")
        return 2

    age = time.time() - float(last_response_at)
    print(f"heartbeat    last LLM response {age / 60:.1f} min ago")

    served, window = _server_activity(args.container)
    if served is not None:
        print(f"server       {served} completions in the {window}")

    print()
    if age <= args.stale_after:
        print(f"ALIVE. A response arrived {age / 60:.1f} min ago.")
        if in_progress is not None:
            print(f"A quiet journal is EXPECTED mid-tick: tick {in_progress} journals nothing")
            print("until its whole phase finishes (cast_votes decides the entire population first).")
        return 0

    if served:
        print(f"ALIVE, despite a {age / 60:.1f} min heartbeat gap: the server completed {served}")
        print(f"requests in the {window}, so work IS happening. Suspect the heartbeat, not the run.")
        return 0

    print(f"SUSPECT. No LLM response for {age / 60:.1f} min (threshold {args.stale_after / 60:.0f} min).")
    if served == 0:
        print(f"The server also logged no completions in the {window} -- consistent with a real stall.")
    else:
        print("The server could not be consulted, so this is NOT yet confirmed.")
    print()
    print("Before killing anything, confirm with the server itself:")
    print(f"  docker logs --since 5m {args.container} | grep -c 'POST /v1/chat/completions'")
    print("  nvidia-smi --query-gpu=utilization.gpu --format=csv")
    print("A nonzero, ADVANCING completion count means the run is fine. Do not use CPU")
    print("time or socket age to decide this -- both are misleading for this workload.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
