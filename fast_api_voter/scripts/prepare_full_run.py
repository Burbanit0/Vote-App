#!/usr/bin/env python3
"""Pre-flight for the full run: 30 simulated years, population 500, 75 chamber seats, LLM engine.

Read-only: builds and validates the config, looks at the server, the disk and the process
tree, and starts nothing. Each check answers a way an earlier long run was lost or muddied
(docs/plan/polity/plan-full-run.md has the list): an unvalidated config, a server that is not
the pinned build, a second job on the GPU, a full disk (OBS-016), a run started from an editor's
process tree (OBS-014), output written to a place that outlives nothing.

Usage (from fast_api_voter/):
    python scripts/prepare_full_run.py [--years N] [--run-id ID] [--output-dir DIR] [--seed N]
        [--workers N] [--reproducibility strict|relaxed] [--resume] [--allow-unpushed]

Prints PASS / WARN / FAIL per check and exits 1 if any FAIL. scripts/launch_full_run.sh runs it first.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # fast_api_voter/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity import llm_call_log  # noqa: E402
from api.domain.polity.config import PolityConfig, validate_config  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

CONTAINER = "vllm-polity"
DEFAULT_OUTPUT = Path.home() / "Documents" / "Dev" / "polity-runs" / "full"
FAIL_GB, WARN_GB = (
    10,
    25,
)  # free disk: below FAIL_GB the run cannot be trusted to finish
EDITOR_ANCESTORS = {"code", "code-insiders", "cursor", "claude", "electron"}
JOBS = re.compile(
    r"run_polity_(flagship|seed_sweep)|run_bakeoff|run_concurrency|check_vllm|check_pressure"
)

_failed = False


def report(status: str, name: str, detail: str) -> None:
    global _failed
    _failed = _failed or status == "FAIL"
    print(f"{status:4s}  {name:9s} {detail}")


def sh(*cmd: str, cwd: Path | None = None) -> str:
    try:
        done = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=cwd, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip()


def free_gb(path: Path) -> float:
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free / 2**30


def check_git(allow_unpushed: bool) -> None:
    head = sh("git", "rev-parse", "--short", "HEAD", cwd=ROOT)
    branch = sh("git", "branch", "--show-current", cwd=ROOT) or "(detached)"
    if sh("git", "status", "--porcelain", cwd=ROOT):
        return report(
            "FAIL",
            "git",
            f"{head} on {branch} has uncommitted changes; the run records this commit",
        )
    if "origin/" not in sh("git", "branch", "-r", "--contains", "HEAD", cwd=ROOT):
        status = "WARN" if allow_unpushed else "FAIL"
        return report(
            status,
            "git",
            f"{head} is not on any origin branch; push it so the run is reproducible",
        )
    report("PASS", "git", f"{head} on {branch}, clean, pushed")


def check_config(args: argparse.Namespace) -> PolityConfig | None:
    try:
        config = _flagship_config(
            engine="llm",
            years=args.years,
            population=500,
            seats=75,
            seed=args.seed,
            output_dir=args.output_dir,
            max_batch_replays=2,
            provider=None,
            workers=args.workers,
            reproducibility=args.reproducibility,
        )
        validate_config(config)
    except Exception as error:  # noqa: BLE001 -- any failure here means the run must not start
        report("FAIL", "config", f"{type(error).__name__}: {error}")
        return None
    llm, vote = config.llm, config.vote
    report(
        "PASS",
        "config",
        f"{config.run.duration_years}y x {config.run.ticks_per_year} = "
        f"{config.run.duration_years * config.run.ticks_per_year} ticks, pop {config.run.population_size}, "
        f"{config.sortition_chamber.seats} seats, seed {config.run.seed}",
    )
    report(
        "PASS",
        "settings",
        f"{llm.reproducibility}, {config.parallel.intra_run_workers} worker(s), "
        f"replays {llm.max_batch_replays}, thinking budget {llm.thinking_token_budget}, "
        f"vote {vote.mode} (turnout cost {vote.turnout_cost}), term limit {config.institutions.president_term_limit}",
    )
    return config


def check_server(config: PolityConfig | None) -> None:
    raw = sh("docker", "inspect", CONTAINER)
    if not raw:
        return report(
            "FAIL",
            "server",
            f"container {CONTAINER} not found; start it with docker-compose.llm.yml",
        )
    info = json.loads(raw)[0]
    health = info["State"].get("Health", {}).get("Status")
    image, command = info["Config"]["Image"], info["Config"].get("Cmd") or []
    if not info["State"]["Running"] or health != "healthy":
        return report(
            "FAIL", "server", f"{CONTAINER} is {info['State']['Status']} / {health}"
        )
    pinned = re.search(
        r"image:\s*(vllm/vllm-openai:\S+)",
        (ROOT / "docker-compose.llm.yml").read_text(),
    )
    mode = "no speculation"
    if "--speculative-config" in command:
        method = re.search(
            r'"method":\s*"(\w+)"', command[command.index("--speculative-config") + 1]
        )
        mode = method.group(1) if method else "speculative (unparsed)"
    if config is not None:
        try:
            with urllib.request.urlopen(
                config.llm.base_url.rstrip("/") + "/models", timeout=10
            ) as reply:
                served = reply.read().decode()
        except OSError as error:
            return report("FAIL", "server", f"/models unreachable: {error}")
        if config.llm.model not in served:
            return report("FAIL", "server", f"model {config.llm.model} is not served")
    same = pinned is not None and pinned.group(1) == image
    report(
        "PASS" if same else "WARN",
        "server",
        f"{image} healthy, {mode}"
        + (
            ""
            if same
            else f" (docker-compose.llm.yml pins {pinned and pinned.group(1)})"
        ),
    )
    if mode != "eagle3":
        report(
            "WARN",
            "server",
            f"the run is planned on EAGLE-3 (adopted 2026-09-26) and this server runs {mode}: "
            "recreate it from docker-compose.llm.yml",
        )


def check_logging() -> None:
    """What the run leaves behind for a close reading, and the tools its helper units need."""
    missing = [
        tool for tool in ("jq", "nvidia-smi", "docker") if not shutil.which(tool)
    ]
    if missing:
        report(
            "FAIL",
            "logging",
            f"{missing} not found: the server-log and telemetry units need them",
        )
    if hasattr(llm_call_log, "PROMPT_LOG_ENV"):
        report(
            "PASS",
            "logging",
            f"call log + prompts ({llm_call_log.PROMPT_LOG_ENV}), server log, GPU/progress sample",
        )
    else:
        report(
            "WARN",
            "logging",
            "this checkout has no prompts sidecar (PR #655): the run would record no prompts",
        )


def check_contention() -> None:
    busy = [
        line.strip()[:110]
        for line in sh("ps", "-eo", "pid,args").splitlines()
        if JOBS.search(line)
        and str(os.getpid()) not in line.split()[:1]
        and "prepare_full_run" not in line
    ]
    report(
        "FAIL" if busy else "PASS",
        "gpu",
        f"another job holds the server: {busy[0]}"
        if busy
        else "no other polity job running",
    )


def check_disk(output_dir: Path) -> None:
    for label, path in (("output", output_dir), ("docker", Path("/var/lib/docker"))):
        if label == "docker" and not path.exists():
            continue
        free = free_gb(path)
        status = "FAIL" if free < FAIL_GB else "WARN" if free < WARN_GB else "PASS"
        report(
            status,
            "disk",
            f"{free:.0f} GiB free for {label} ({path}); floor {FAIL_GB}, comfortable {WARN_GB}",
        )
    if str(output_dir.resolve()).startswith("/tmp"):
        report(
            "FAIL",
            "output",
            "output is under /tmp, which is RAM and is wiped on reboot",
        )
    elif sh(
        "git",
        "rev-parse",
        "--show-toplevel",
        cwd=output_dir if output_dir.exists() else output_dir.parent,
    ):
        report(
            "WARN",
            "output",
            "output is inside a git worktree: removing that worktree deletes the run",
        )
    else:
        report("PASS", "output", f"{output_dir} is outside any worktree and off /tmp")


def check_run_dir(output_dir: Path, run_id: str, resume: bool) -> None:
    run_dir = output_dir / run_id
    if resume:
        ok = any(run_dir.rglob("checkpoint.json")) if run_dir.exists() else False
        return report(
            "PASS" if ok else "FAIL",
            "run dir",
            f"{run_dir} "
            + ("has a checkpoint to resume" if ok else "has nothing to resume"),
        )
    report(
        "FAIL" if run_dir.exists() else "PASS",
        "run dir",
        f"{run_dir} "
        + ("exists; use --resume or a new --run-id" if run_dir.exists() else "is free"),
    )


def check_process_tree() -> None:
    names, pid = [], os.getpid()
    while pid > 1:
        try:
            names.append(Path(f"/proc/{pid}/comm").read_text().strip())
            pid = int(
                Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1]
            )
        except (OSError, ValueError):
            break
    hit = EDITOR_ANCESTORS & set(names)
    report(
        "WARN" if hit else "PASS",
        "process",
        f"this shell descends from {sorted(hit)}: an editor OOM would SIGTERM the run (OBS-014); use launch_full_run.sh"
        if hit
        else "not under an editor's process tree",
    )
    if not sh("systemd-run", "--user", "--version"):
        return report(
            "FAIL",
            "systemd",
            "systemd-run --user is unavailable, so the run cannot be detached properly",
        )
    linger = sh("loginctl", "show-user", getpass.getuser(), "-p", "Linger")
    report(
        "PASS" if linger.endswith("yes") else "WARN",
        "systemd",
        "lingering on"
        if linger.endswith("yes")
        else "Linger=no: logging out of the desktop session stops the run "
        "(loginctl enable-linger $USER fixes it)",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--years", type=int, default=30, help="30 is the full run, 2 the timing probe"
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument(
        "--reproducibility", choices=("strict", "relaxed"), default="relaxed"
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--allow-unpushed",
        action="store_true",
        help="a WARN, not a FAIL, for an unpushed commit (testing)",
    )
    args = parser.parse_args()
    args.run_id = (
        args.run_id
        or f"full-{args.years}y-p500-seed{args.seed}-{datetime.now(timezone.utc):%Y%m%d}"
    )
    print(f"Pre-flight for run {args.run_id} -> {args.output_dir}\n")
    check_git(args.allow_unpushed)
    config = check_config(args)
    check_server(config)
    check_logging()
    check_contention()
    check_disk(args.output_dir)
    check_run_dir(args.output_dir, args.run_id, args.resume)
    check_process_tree()
    print(
        "\n"
        + (
            "NOT READY: fix the FAIL lines above."
            if _failed
            else "READY: scripts/launch_full_run.sh --go"
        )
    )
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
