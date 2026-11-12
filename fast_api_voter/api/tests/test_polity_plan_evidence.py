"""The build-order plan's evidence rule, checked (S5.4): a step's Closed-by cell holds
exactly one thing, the merge commit that closed it. A wrong SHA there is a false claim
the plan makes about itself, and nothing else would catch it."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PLAN = REPO / "docs" / "plan" / "polity" / "plan-polity-build-order.md"
_STEP_ROW = re.compile(r"^\| (S\d\.\d) \| [^|]+ \| [^|]* \| ([^|]+) \| ([^|]*) \|$")


def _git(*args: str) -> str | None:
    try:
        completed = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _closed_steps() -> list[tuple[str, str, str]]:
    rows = []
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        match = _STEP_ROW.match(line)
        if match and match.group(3).strip():
            rows.append((match.group(1), match.group(2).strip().strip("`"), match.group(3).strip()))
    return rows


def test_closed_by_cells_hold_only_a_commit() -> None:
    closed = _closed_steps()
    assert closed, "no closed steps found -- has the steps table's format changed?"
    for step, _branch, cell in closed:
        assert re.fullmatch(r"`[0-9a-f]{7,40}`", cell), f"{step}: Closed by must be one backticked SHA, got {cell!r}"


@pytest.mark.parametrize(("step", "branch", "cell"), _closed_steps())
def test_each_closed_by_commit_is_the_merge_of_that_steps_branch(step: str, branch: str, cell: str) -> None:
    sha = cell.strip("`")
    if _git("cat-file", "-e", f"{sha}^{{commit}}") is None:
        pytest.skip(f"{sha} is not in this clone (a shallow CI checkout does not fetch old merges)")
    parents, subject = (_git("log", "-1", "--format=%P%n%s", sha) or "\n").split("\n", 1)
    assert len(parents.split()) == 2, f"{step}: {sha} is not a merge commit"
    assert f"({step}" in subject, f"{step}: {sha}'s subject does not name the step: {subject!r}"
    if not branch.startswith("("):
        assert branch in subject, f"{step}: {sha}'s subject does not name {branch}: {subject!r}"
