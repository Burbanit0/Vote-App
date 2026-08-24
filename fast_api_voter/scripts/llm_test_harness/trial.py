"""
fast_api_voter/scripts/llm_test_harness/trial.py

Records one trial: captures environment before and after a caller-supplied
LLM call, stores everything, returns the result unchanged. The harness
itself never calls an LLM -- `run_call` is how a specific experiment plugs
its own protocol (a positioning batch, a vote_cast chunk, a raw
completion, whatever shape a future protocol needs) into the harness's
own bookkeeping, keeping the generic/protocol-specific boundary exactly
where the design brief asks for it: "run" is this function, called in a
loop by a protocol-specific script -- never a generic CLI subcommand (see
cli.py's own docstring for why).
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import environment, storage


@dataclass(frozen=True)
class TrialResult:
    ok: bool
    finish_reason: str | None = None
    truncated: bool | None = None
    decoded_tokens: int | None = None
    detail: str = ""


def record_trial(
    experiment_id: str,
    trial_number: int,
    *,
    container_name: str,
    run_call: Callable[[], TrialResult],
    inference_backend: str = "ollama",
    inference_config: dict[str, str] | None = None,
    env_runner: environment.CommandRunner = environment.DEFAULT_RUNNER,
    db_path: Path | None = None,
) -> TrialResult:
    """Captures environment, runs run_call(), captures environment again,
    times the call, stores the whole trial row, and returns the
    TrialResult unchanged.

    Deliberately does NOT catch exceptions from run_call: a genuinely
    unexpected failure (a transport error the caller didn't already turn
    into TrialResult(ok=False, ...)) propagates rather than being silently
    recorded as a measured trial outcome -- the caller's own run_call is
    what decides what counts as a "trial failure" versus a real bug in the
    calling code, exactly the distinction LlmResponseError's own
    "NOT retried" ruling (llm_client.py) already draws for the production
    codebase.

    `env_runner` is injected the same way environment.capture's own
    `runner` is, for the same reason (see environment.py)."""
    before = environment.capture(
        container_name, inference_backend=inference_backend,
        inference_config=inference_config, runner=env_runner,
    )
    started_at = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    result = run_call()
    latency = time.monotonic() - start
    finished_at = datetime.now(timezone.utc).isoformat()
    after = environment.capture(
        container_name, inference_backend=inference_backend,
        inference_config=inference_config, runner=env_runner,
    )

    conn = storage.connect(db_path)
    try:
        storage.insert_trial(
            conn,
            {
                "experiment_id": experiment_id,
                "trial_number": trial_number,
                "started_at": started_at,
                "finished_at": finished_at,
                "environment_before": before.to_json(),
                "environment_after": after.to_json(),
                "ok": int(result.ok),
                "finish_reason": result.finish_reason,
                "truncated": None if result.truncated is None else int(result.truncated),
                "latency_seconds": latency,
                "decoded_tokens": result.decoded_tokens,
                "detail": result.detail,
            },
        )
    finally:
        conn.close()

    return result
