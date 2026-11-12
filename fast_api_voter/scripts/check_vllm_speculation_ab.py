"""One timed LLM run against whatever vLLM server is on :8000, for the n-gram speculation A/B.

The same flagship LLM config every time (population 100, 30 seats, seed 1, 12 relaxed workers);
only the server behind it changes between arms. Prints one `AB_RESULT` line and writes
`ab_summary.json` (wall clock, calls, tokens, and per-decision-type latency and decode rate) beside
the run. See check_vllm_speculation_ab_results.md for the arms and their outcome.

Usage (from fast_api_voter/; needs the vLLM server, GPU, and nothing else on it):
    python scripts/check_vllm_speculation_ab.py <label> <years> <out_dir>
    python scripts/check_vllm_speculation_ab.py A1 2 /tmp/ab/A1
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import validate_config  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402


def main(label: str, years: int, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    config = _flagship_config(
        engine="llm", years=years, population=100, seats=30, seed=1, output_dir=out,
        max_batch_replays=2, provider=None, workers=12, reproducibility="relaxed",
    )
    validate_config(config)

    start = time.monotonic()
    journal = Path(run_simulation(config, run_id=label))
    wall = time.monotonic() - start

    calls = [json.loads(line) for line in (journal.parent / "llm_calls.jsonl").read_text().splitlines() if line.strip()]
    events = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
    by_type: dict[str, dict[str, float]] = defaultdict(lambda: {"calls": 0, "latency_s": 0.0, "completion_tokens": 0, "prompt_tokens": 0})
    for call in calls:
        d = by_type[call.get("decision_type") or call.get("kind")]
        d["calls"] += 1
        d["latency_s"] += (call.get("latency_ms") or 0) / 1000
        d["completion_tokens"] += call.get("completion_tokens") or 0
        d["prompt_tokens"] += call.get("prompt_tokens") or 0
    total_out = sum(d["completion_tokens"] for d in by_type.values())
    summary = {
        "label": label, "years": years, "wall_s": round(wall, 1), "calls": len(calls),
        "completion_tokens": total_out, "prompt_tokens": sum(d["prompt_tokens"] for d in by_type.values()),
        "throughput_tok_s": round(total_out / wall, 1),
        "elections": sum(e["event_type"] == "elected" for e in events),
        "recalls": sum(e["event_type"] == "recalled" for e in events),
        "by_type": {
            name: {**d, "latency_s": round(d["latency_s"], 1),
                   "tok_per_s_per_call": round(d["completion_tokens"] / d["latency_s"], 1) if d["latency_s"] else None}
            for name, d in sorted(by_type.items(), key=lambda item: -item[1]["latency_s"])
        },
    }
    (out / "ab_summary.json").write_text(json.dumps(summary, indent=2))
    print("AB_RESULT", json.dumps({k: summary[k] for k in ("label", "wall_s", "calls", "completion_tokens", "throughput_tok_s", "elections", "recalls")}), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), Path(sys.argv[3]))
