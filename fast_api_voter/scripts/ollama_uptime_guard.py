"""
scripts/ollama_uptime_guard.py

Pragmatic mitigation, NOT a fix for the specific incident that motivated it -- the `ollama-polity`
Docker container died mid-generation (exit code 255, no OOM flag, GPU/disk both healthy) during the
second v6b acceptance run's final tick, propagating as `LlmTransportError` (`WinError 10054`,
connection forcibly closed) up through `run_polity_simulation.py`, four hours into an unfinished
run with no checkpoint/resume mechanism. **That specific incident's cause is confirmed, not merely
suspected**: the user ran `wsl --shutdown` in a sibling worktree (`Vote-App`) while this run was
active, which tears down the shared `docker-desktop` WSL2 distro -- and with it every Docker
Desktop container on the machine, regardless of which repo/worktree the `wsl --shutdown` was run
from -- from outside Docker's own supervision (see `llm_batching_determinism_results_gpu.md`'s own
dated section, "Un septieme mode de defaillance"). No uptime-based restart schedule prevents THAT
trigger: an external `wsl --shutdown` kills a freshly-started container exactly as readily as a
26h-old one.

This script exists anyway, because the bounded search that investigated the incident surfaced a
SEPARATE, real, independently-documented risk category: WSL2/Docker Desktop connectivity degrading
over long uptime (multiple upstream GitHub issues, cited in the same dated section) is a known
failure class distinct from an explicit `wsl --shutdown`. `recycle_after_n_calls` (bug 4's own
mitigation, `polity_config.yaml`) already recycles the MODEL's own prompt cache periodically by
call count; this is the same idea one level up, on a fixed wall-clock schedule, as a hedge against
that separate, still-plausible risk -- not a response to the incident that actually happened here.

Two ways this gets exercised:

1. As a pre-flight check inside any acceptance script before starting an expensive --engine llm
   run (see run_v6b_acceptance.py's own call site) -- cheap, and directly protects the run about to
   be launched.
2. As a standalone, periodically-scheduled check, independent of whether any run is currently
   active -- registered as a Windows Scheduled Task (see the README section below), because the
   crash that motivated this script happened after 26h of container uptime accumulated mostly
   BETWEEN work sessions, not during one continuous run. A pre-flight check alone would have caught
   this specific crash (the run was ~4h, well under 12h), but would not catch staleness that
   accumulates while nothing is running.

Usage (manual or pre-flight):
    python fast_api_voter/scripts/ollama_uptime_guard.py --max-uptime-hours 12

Usage (standalone, for Task Scheduler -- see README below):
    python fast_api_voter/scripts/ollama_uptime_guard.py --max-uptime-hours 12 --quiet

Registering the scheduled task (run once, from an elevated or normal PowerShell -- `schtasks`
does not require admin for a per-user task):
    schtasks /create /tn "PolityOllamaUptimeGuard" /sc HOURLY /mo 1 /f /tr ^
        "C:\\Python314\\python.exe C:\\Users\\burba\\Vote-App-polity\\fast_api_voter\\scripts\\ollama_uptime_guard.py --max-uptime-hours 12 --quiet"

Removing it:
    schtasks /delete /tn "PolityOllamaUptimeGuard" /f

This is deliberately a fixed wall-clock threshold (12h, chosen as "half of the one observed
crash's own uptime, with margin," not measured against a second data point) -- it does not adapt
to call volume, prompt shape, or anything else `recycle_after_n_calls` already handles at the
model layer. If a future crash occurs well under 12h of uptime, this mitigation does nothing for
it and the threshold (or the whole "uptime is the operative variable" hypothesis) needs revisiting.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_CONTAINER = "ollama-polity"
DEFAULT_MAX_UPTIME_HOURS = 12.0
DEFAULT_HEALTH_URL = "http://localhost:11434/api/version"


def container_uptime_hours(container: str) -> float:
    """Raises RuntimeError if the container does not exist or `docker inspect` fails -- a guard
    that silently reports "0 hours uptime" for a container it can't actually see would never
    trigger a restart when one is needed, which is worse than a loud failure."""
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.StartedAt}}", container],
        capture_output=True, text=True, timeout=10.0,
    )
    if result.returncode != 0:
        raise RuntimeError(f"docker inspect {container!r} failed: {result.stderr.strip()}")
    started_at_raw = result.stdout.strip()
    # Docker emits RFC3339 with nanosecond precision ("...229T22:22:23.221718959Z"), which
    # datetime.fromisoformat cannot parse directly (max 6 fractional digits) -- truncate to
    # microseconds before parsing.
    if "." in started_at_raw:
        head, frac_and_zone = started_at_raw.split(".", 1)
        frac = frac_and_zone.rstrip("Z")[:6]
        started_at_raw = f"{head}.{frac}+00:00"
    else:
        started_at_raw = started_at_raw.rstrip("Z") + "+00:00"
    started_at = datetime.fromisoformat(started_at_raw)
    return (datetime.now(timezone.utc) - started_at).total_seconds() / 3600.0


def wait_until_healthy(url: str = DEFAULT_HEALTH_URL, *, timeout_seconds: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5.0) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1.0)
    return False


def ensure_fresh_container(
    container: str = DEFAULT_CONTAINER, *, max_uptime_hours: float = DEFAULT_MAX_UPTIME_HOURS,
    dry_run: bool = False, quiet: bool = False,
) -> bool:
    """Returns True iff a restart was performed (or, under --dry-run, would have been). Restarting
    a container that is already healthy and under the threshold is a no-op by construction -- this
    function never restarts pre-emptively "just in case," only past the measured threshold."""
    uptime = container_uptime_hours(container)
    if uptime < max_uptime_hours:
        if not quiet:
            print(f"{container}: uptime {uptime:.1f}h < {max_uptime_hours:.1f}h threshold -- no restart needed.")
        return False

    if not quiet:
        print(f"{container}: uptime {uptime:.1f}h >= {max_uptime_hours:.1f}h threshold -- restarting.")
    if dry_run:
        if not quiet:
            print(f"{container}: --dry-run, not actually restarting.")
        return True

    result = subprocess.run(["docker", "restart", container], capture_output=True, text=True, timeout=60.0)
    if result.returncode != 0:
        raise RuntimeError(f"docker restart {container!r} failed: {result.stderr.strip()}")
    healthy = wait_until_healthy()
    if not quiet:
        status = "responding" if healthy else "NOT responding after 30s -- check manually"
        print(f"{container}: restarted, {status}.")
    if not healthy:
        raise RuntimeError(f"{container} restarted but did not become healthy within 30s.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--max-uptime-hours", type=float, default=DEFAULT_MAX_UPTIME_HOURS)
    parser.add_argument("--dry-run", action="store_true", help="report what would happen, don't restart")
    parser.add_argument("--quiet", action="store_true", help="only print on actual restart or error")
    args = parser.parse_args()
    try:
        ensure_fresh_container(
            args.container, max_uptime_hours=args.max_uptime_hours, dry_run=args.dry_run, quiet=args.quiet,
        )
    except RuntimeError as exc:
        print(f"ollama_uptime_guard: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
