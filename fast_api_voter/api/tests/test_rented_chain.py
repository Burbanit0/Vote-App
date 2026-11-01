"""scripts/rented/chain.sh (plan-rented-gpu-runs.md §10): seeds run to completion, a finished seed is skipped on a
restart, and a seed that died before its first checkpoint starts over. Deterministic engine: no model server."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # the repo
CHAIN = ROOT / "fast_api_voter" / "scripts" / "rented" / "chain.sh"


def _chain(out: Path, seeds: str) -> str:
    env = {**os.environ, "RUN_LABEL": "t", "SEEDS": seeds, "YEARS": "1", "POPULATION": "40", "SEATS": "6",
           "ENGINE": "deterministic", "WORKERS": "1", "RETRY_PAUSE": "0", "PY": sys.executable, "REPO": str(ROOT), "OUT": str(out)}
    return subprocess.run(["bash", str(CHAIN)], env=env, capture_output=True, text=True, check=True, timeout=300).stdout


def test_seeds_complete_resume_and_restart(tmp_path: Path) -> None:
    first = _chain(tmp_path, "1")
    assert "seed 1 attempt 1" in first and (tmp_path / "CHAIN_DONE").is_file()
    assert "attempt" not in _chain(tmp_path, "1")  # completed: skipped on a restart
    (tmp_path / "seed2" / "run" / "seed2").mkdir(parents=True)  # died before its first checkpoint
    again = _chain(tmp_path, "2")
    assert "seed 2 attempt 1 --force" in again and "seed 2 done" in again
