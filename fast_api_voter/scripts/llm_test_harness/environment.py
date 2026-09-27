"""
fast_api_voter/scripts/llm_test_harness/environment.py

Automatic environment-state capture, run before and after every trial --
the piece this project's own GPU investigation (2026-08-17/19) was missing
until a confounding factor (a Windows Defender scan) was reconstructed
after the fact from Windows event logs and Docker log timestamps (see
llm_batching_determinism_results_gpu.md's own "test de stationnarité"
section). A confounding factor found only in hindsight cannot be
controlled for; this module exists so the next one is in the data from
the start, not rediscovered by forensics.
"""
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TypeAlias

CommandRunner: TypeAlias = Callable[[Sequence[str]], str]


def _real_runner(command: Sequence[str]) -> str:
    """Default runner: a real subprocess call. Swallows failure into an
    empty string rather than raising -- environment capture is
    best-effort observability, never allowed to abort the trial it is
    describing (the same "never fatal" register run_polity_simulation.py's
    own _warm_up_llm_client already uses, for the identical reason)."""
    try:
        result = subprocess.run(
            list(command), capture_output=True, text=True, timeout=10.0, check=False,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


DEFAULT_RUNNER: CommandRunner = _real_runner


@dataclass(frozen=True)
class EnvironmentSnapshot:
    captured_at: str
    container_name: str
    container_uptime_seconds: float | None
    cached_prompts_count: int | None
    gpu_utilization_percent: float | None
    gpu_memory_used_mib: float | None
    gpu_temperature_c: float | None
    concurrent_processes: tuple[str, ...]
    git_commit: str
    inference_backend: str
    inference_config: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def _parse_uptime_seconds(started_at_raw: str, now: datetime) -> float | None:
    """`docker inspect --format {{.State.StartedAt}}` returns RFC3339 with
    nanosecond precision, which Python's datetime only supports to
    microseconds -- truncates the fractional-seconds part defensively.
    Returns None (never raises) for an empty or malformed input, since a
    container not found / docker unavailable must degrade the snapshot,
    not abort it."""
    if not started_at_raw:
        return None
    try:
        cleaned = started_at_raw.replace("Z", "+00:00")
        if "." in cleaned:
            head, _, tail = cleaned.partition(".")
            frac, _, offset = tail.partition("+")
            cleaned = f"{head}.{frac[:6]}+{offset}" if offset else f"{head}.{frac[:6]}"
        started = datetime.fromisoformat(cleaned)
        return (now - started).total_seconds()
    except ValueError:
        return None


def _parse_cached_prompts(logs: str) -> int | None:
    """Looks for the most recent "cache state: N prompts" line --
    llama.cpp server's own log format, observed directly this session
    (see llm_batching_determinism_results_gpu.md's "third mechanism"
    section). None if the pattern never appears (a different backend, or
    logs unavailable)."""
    match: str | None = None
    for line in logs.splitlines():
        if "cache state:" in line and "prompts" in line:
            match = line
    if match is None:
        return None
    try:
        segment = match.split("cache state:")[1]
        digits = "".join(ch for ch in segment.split("prompts")[0] if ch.isdigit())
        return int(digits) if digits else None
    except (IndexError, ValueError):
        return None


def _parse_gpu_csv(raw: str) -> tuple[float | None, float | None, float | None]:
    """Parses one `nvidia-smi --query-gpu=utilization.gpu,memory.used,
    temperature.gpu --format=csv,noheader,nounits` line into
    (utilization_percent, memory_used_mib, temperature_c). Each field is
    None if missing/unparseable (no GPU, nvidia-smi absent, unexpected
    output shape)."""
    line = raw.strip().splitlines()[0] if raw.strip() else ""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != 3:
        return None, None, None

    def _to_float(value: str) -> float | None:
        try:
            return float(value)
        except ValueError:
            return None

    return _to_float(parts[0]), _to_float(parts[1]), _to_float(parts[2])


def capture(
    container_name: str,
    *,
    inference_backend: str = "ollama",
    inference_config: dict[str, str] | None = None,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> EnvironmentSnapshot:
    """Captures the current environment state in one call: container
    uptime, cached-prompt count (parsed from the container's own recent
    logs), GPU utilization/memory/temperature, concurrently-running
    processes with a significant GPU footprint, the current git commit,
    and the inference backend's own config. Every field degrades to
    None/empty on any single command's failure rather than raising -- see
    _real_runner's own docstring for why. `runner` is injected so tests
    never touch a real GPU/Docker/git (see tests/test_environment.py's own
    fake-runner fixtures)."""
    now = datetime.now(timezone.utc)

    started_at_raw = runner(["docker", "inspect", "--format", "{{.State.StartedAt}}", container_name])
    uptime = _parse_uptime_seconds(started_at_raw, now)

    logs = runner(["docker", "logs", "--tail", "200", container_name])
    cached_prompts = _parse_cached_prompts(logs)

    gpu_csv = runner([
        "nvidia-smi",
        "--query-gpu=utilization.gpu,memory.used,temperature.gpu",
        "--format=csv,noheader,nounits",
    ])
    gpu_util, gpu_mem, gpu_temp = _parse_gpu_csv(gpu_csv)

    processes_raw = runner(["nvidia-smi", "--query-compute-apps=process_name", "--format=csv,noheader"])
    processes = tuple(line.strip() for line in processes_raw.splitlines() if line.strip())

    git_commit = runner(["git", "rev-parse", "HEAD"]).strip() or "unknown"

    return EnvironmentSnapshot(
        captured_at=now.isoformat(),
        container_name=container_name,
        container_uptime_seconds=uptime,
        cached_prompts_count=cached_prompts,
        gpu_utilization_percent=gpu_util,
        gpu_memory_used_mib=gpu_mem,
        gpu_temperature_c=gpu_temp,
        concurrent_processes=processes,
        git_commit=git_commit,
        inference_backend=inference_backend,
        inference_config=inference_config or {},
    )
