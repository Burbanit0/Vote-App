"""Every script in fast_api_voter/scripts/ still imports (CI plan, phase 12b).

The scripts sit outside coverage and outside mypy (except the LLM test
harness), so a renamed or removed symbol in api/ breaks them silently: the
next person to run an experiment finds out, weeks later. Importing each one
catches that class of break for every script at the cost of a module load.

Each import runs in its own interpreter: scripts set up sys.path, logging and
environment checks at import time, and one must not leak into the next.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"

# A script that cannot be imported in the test environment, with the reason.
# Keep it short: everything else must import.
KNOWN_UNIMPORTABLE = {
    # Locust is not in any lockfile: the load test is run by hand (EXP-007).
    "loadtest_v2_engine.py": "needs locust",
}

IMPORT = """
import importlib.util, sys
sys.path[:0] = [{scripts!r}, {root!r}]
name = {name!r}
spec = importlib.util.spec_from_file_location(name, {path!r})
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module  # pydantic/dataclasses resolve forward refs through it
spec.loader.exec_module(module)
"""


def _scripts() -> list[str]:
    return sorted(p.name for p in SCRIPTS.glob("*.py") if p.name not in KNOWN_UNIMPORTABLE)


@pytest.mark.parametrize("script", _scripts())
def test_script_imports(script: str) -> None:
    path = SCRIPTS / script
    code = IMPORT.format(scripts=str(SCRIPTS), root=str(SCRIPTS.parent), name=path.stem, path=str(path))
    # gen_engine_parity.py refuses to load without the seed pinned (its fixture
    # must be reproducible); every other script ignores it.
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    res = subprocess.run([sys.executable, "-c", code], cwd=SCRIPTS, env=env,
                         capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, f"{script} no longer imports:\n{res.stderr[-2000:]}"


def test_the_known_unimportable_list_names_real_files() -> None:
    assert all((SCRIPTS / name).is_file() for name in KNOWN_UNIMPORTABLE)
