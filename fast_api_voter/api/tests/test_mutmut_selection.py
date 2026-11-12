"""mutmut's test list stays in step with the rule that derives it.

pyproject.toml's [tool.mutmut] pytest_add_cli_args_test_selection is a hand-kept
list, with the rule that should produce it written next to it: every test file
that imports an engine module directly and touches neither FastAPI/TestClient
nor numpy (EXP-015: those break mutmut's in-process reload). The list drifted
three times; each time, tests written for a rule never ran against that rule's
mutants (the third time, test_borda.py against Borda's). This applies the rule
and fails on any file it selects that is neither listed nor excluded below.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # fast_api_voter/

ENGINE_IMPORT = re.compile(r"simulation_(ranked|score)_utils")
RELOAD_BREAKERS = re.compile(r"TestClient|from fastapi|import numpy|from api\.main")

# Selected by the rule, deliberately not run per mutant. Keep the reason.
EXCLUDED = {
    # Wall-clock ceilings: mutmut's trampolines slow every call, so a mutant
    # could be "killed" by a timing assert, not by a behaviour check.
    "api/tests/test_engine_benchmarks.py": "wall-clock assertions",
    # Both call every rule of the engine, so mutmut would pick them for nearly
    # every mutant: ~25 s and ~8 s per run, hours over ~2,000 survivors.
    "api/tests/test_voting_criteria_matrix.py": "too slow per mutant (~25 s, whole engine)",
    "api/tests/test_compare_all_methods_snapshot.py": "too slow per mutant (~8 s, whole engine)",
}


def _listed() -> list[str]:
    conf = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    selection: list[str] = conf["tool"]["mutmut"]["pytest_add_cli_args_test_selection"]
    return selection


def _derived() -> set[str]:
    found = set()
    for path in sorted((ROOT / "api" / "tests").glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        if ENGINE_IMPORT.search(text) and not RELOAD_BREAKERS.search(text):
            found.add(path.relative_to(ROOT).as_posix())
    return found


def test_every_file_the_rule_selects_is_listed_or_excluded() -> None:
    missing = sorted(_derived() - set(_listed()) - set(EXCLUDED))
    assert not missing, (
        "These test files import the engine and would run under mutmut, but "
        "[tool.mutmut] pytest_add_cli_args_test_selection does not list them: "
        f"{missing}. Add them there, or to EXCLUDED here with the reason."
    )


def test_exclusions_are_still_selected_by_the_rule() -> None:
    stale = sorted(set(EXCLUDED) - _derived())
    assert not stale, f"EXCLUDED names files the rule no longer selects: {stale}"


def test_listed_files_exist_once() -> None:
    listed = _listed()
    assert len(listed) == len(set(listed)), "a file is listed twice"
    assert not [p for p in listed if not (ROOT / p).is_file()]
