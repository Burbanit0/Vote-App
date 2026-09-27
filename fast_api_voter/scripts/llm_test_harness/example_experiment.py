"""
fast_api_voter/scripts/llm_test_harness/example_experiment.py

End-to-end smoke test for the harness itself: register -> run (via
trial.record_trial, in a loop, exactly how a real experiment would use
the library) -> report. Uses a FAKE run_call (no GPU, no network,
deterministic) -- this validates the harness's own plumbing, not any real
LLM behavior. A real experiment replaces the fake run_call with a genuine
LLM call and nothing else changes.

Usage:
    python fast_api_voter/scripts/llm_test_harness/example_experiment.py
"""
from __future__ import annotations

import random
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_test_harness import registration, report, trial  # noqa: E402


def _fake_run_call(rng: random.Random) -> trial.TrialResult:
    """Stands in for a real LLM call so this example runs instantly, with
    no GPU: succeeds ~80% of the time, deterministic given the seeded rng
    passed in by main()."""
    ok = rng.random() < 0.8
    return trial.TrialResult(
        ok=ok,
        finish_reason="stop" if ok else "length",
        truncated=not ok,
        decoded_tokens=rng.randint(50, 200),
        detail="" if ok else "fake induced failure for the smoke test",
    )


def _fake_env_runner(command: Sequence[str]) -> str:
    """Stands in for real docker/nvidia-smi/git calls -- see
    environment.py's own CommandRunner protocol."""
    return ""


def main() -> int:
    experiment = registration.register(
        hypothesis="[EXAMPLE/SMOKE TEST] harness plumbing works end to end",
        decision_criterion="failure_rate > 0.5 = the harness itself is broken",
        planned_n=10,
        budget_description="a few seconds, no GPU",
        threshold=0.5,
        comparison="gt",
        metric="failure_rate",
    )
    print(f"Registered {experiment.experiment_id}")

    rng = random.Random(42)
    for i in range(1, experiment.planned_n + 1):
        trial.record_trial(
            experiment.experiment_id,
            i,
            container_name="example-fake-container",
            run_call=lambda: _fake_run_call(rng),
            env_runner=_fake_env_runner,
        )

    text = report.generate_report(experiment.experiment_id)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
