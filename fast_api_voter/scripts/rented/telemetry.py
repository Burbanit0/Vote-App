"""The rented pod's telemetry (plan-rented-gpu-runs.md §10, gap G3): one JSON line a minute for the whole session --
the GPU, vLLM's own counters, and every run's progress -- into /workspace/runs/telemetry.jsonl, beside the runs it
describes, so it is fetched with them. Stdlib only; a sample that cannot be read is recorded as null, never fatal.

Usage (on the pod, started by pod_start.sh): python telemetry.py [--every 60] [--runs /workspace/runs]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

METRICS_URL = "http://127.0.0.1:8000/metrics"
# vLLM's Prometheus names vary across versions; any metric whose name contains one of these is kept, summed over labels.
WANTED = ("requests_running", "requests_waiting", "cache_usage", "prompt_tokens_total", "generation_tokens_total",
          "preemptions_total", "prefix_cache_hits_total", "prefix_cache_queries_total")
GPU_FIELDS = "utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw"


def vllm_metrics(text: str) -> dict[str, float]:
    """The wanted counters from a Prometheus text page, summed over their labels."""
    found: dict[str, float] = {}
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        name, _, rest = line.partition("{") if "{" in line.split(" ", 1)[0] else line.partition(" ")
        if any(w in name for w in WANTED):
            try:
                found[name] = found.get(name, 0.0) + float(rest.rsplit(" ", 1)[-1])
            except ValueError:
                continue
    return found


def gpu() -> list[dict[str, float]] | None:
    try:
        out = subprocess.run(["nvidia-smi", f"--query-gpu={GPU_FIELDS}", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=20, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    keys = GPU_FIELDS.split(",")
    return [dict(zip(keys, (float(v) for v in row.split(",")), strict=False)) for row in out.strip().splitlines()]


def progress(runs: Path) -> dict[str, Any]:
    """Each run's progress.json under `runs` (<label>/seed<N>/run/seed<N>/progress.json), keyed <label>/seed<N>."""
    found: dict[str, Any] = {}
    for path in sorted(runs.glob("*/*/run/*/progress.json")):
        try:
            found[f"{path.parents[3].name}/{path.parent.name}"] = json.loads(path.read_text())
        except (OSError, ValueError):
            found[f"{path.parents[3].name}/{path.parent.name}"] = None
    return found


def sample(runs: Path) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(METRICS_URL, timeout=10) as response:
            metrics: dict[str, float] | None = vllm_metrics(response.read().decode())
    except OSError:
        metrics = None
    return {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"), "gpu": gpu(), "vllm": metrics,
            "progress": progress(runs)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--every", type=int, default=60, help="seconds between samples")
    parser.add_argument("--runs", type=Path, default=Path("/workspace/runs"))
    parser.add_argument("--once", action="store_true", help="print one sample and stop")
    args = parser.parse_args()
    while True:
        line = json.dumps(sample(args.runs))
        if args.once:
            print(line)
            return
        with (args.runs / "telemetry.jsonl").open("a") as out:
            out.write(line + "\n")
        time.sleep(args.every)


if __name__ == "__main__":
    main()
