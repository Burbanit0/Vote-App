"""The criteria registry agrees with this engine's axiom tests (PLAN_BEYOND_CI W1.2).

voter-app/src/data/method_criteria.json is the one source of the Lab's criteria matrix: one
entry per (rule, criterion) with its verdict and how it is known. Every cell the matrix in
test_voting_criteria_matrix.py classifies is marked `engine-tested` there and must say what
that file's sets say -- except the four documented `variant` cells (D8: the textbook
verdict, which this engine's simultaneous elimination of tied last places does not keep).
The client's axiom test checks the same file against its own sets.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

from api.tests.test_voting_criteria_matrix import (
    CONDORCET_LOSER_SATISFIES,
    CONDORCET_WINNER_SATISFIES,
    MAJORITY_SATISFIES,
    METHODS,
    MONOTONICITY_SATISFIES,
)

REPO = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO / "voter-app" / "src" / "data" / "method_criteria.json"
BIBLIOGRAPHY_PATH = REPO / "docs" / "research" / "bibliography.bib"
CRITERIA = ["condorcet_winner", "condorcet_loser", "majority", "monotonicity",
            "iia", "strategy_proof", "participation", "reversal"]


@pytest.fixture(scope="module")
def registry() -> Any:
    """The registry lives outside fast_api_voter/: a backend-only checkout (the dev image)
    skips, but GitHub Actions and ci-local, which have it, never do."""
    if not REGISTRY_PATH.exists() or not BIBLIOGRAPHY_PATH.exists():
        if os.environ.get("GITHUB_ACTIONS"):
            pytest.fail(f"{REGISTRY_PATH} or {BIBLIOGRAPHY_PATH} is missing: moved or renamed?")
        pytest.skip("the criteria registry is not in this checkout (backend only)")
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

SATISFIES = {
    "condorcet_winner": CONDORCET_WINNER_SATISFIES,
    "condorcet_loser": CONDORCET_LOSER_SATISFIES,
    "majority": MAJORITY_SATISFIES,
    "monotonicity": MONOTONICITY_SATISFIES,
}


@pytest.mark.parametrize("criterion", sorted(SATISFIES))
def test_every_engine_tested_cell_says_what_the_matrix_says(registry: Any, criterion: str) -> None:
    for method in METHODS:
        entry = registry["rules"][method][criterion]
        holds = method in SATISFIES[criterion]
        if entry["basis"] == "variant":
            assert not holds, f"{method}.{criterion} is a documented variant: the engine must violate it"
            assert entry["verdict"] == "yes" and entry.get("note"), f"{method}.{criterion}"
        else:
            assert entry["basis"] == "engine-tested", f"{method}.{criterion}"
            assert entry["verdict"] == ("yes" if holds else "no"), f"{method}.{criterion}"


def test_only_this_matrix_can_mark_a_cell_engine_tested_or_variant(registry: Any) -> None:
    """A variant says the engine departs from the textbook, which only a cell this matrix tests
    can show; and every row has exactly the eight criteria the registry declares."""
    assert registry["criteria"] == CRITERIA
    for rule, row in registry["rules"].items():
        assert sorted(row) == sorted(CRITERIA), rule
        for criterion, entry in row.items():
            if entry["basis"] in ("engine-tested", "variant"):
                assert rule in METHODS and criterion in SATISFIES, f"{rule}.{criterion}"


def test_every_cited_source_is_in_the_bibliography(registry: Any) -> None:
    keys = set(re.findall(r"^@\w+\{([^,]+),", BIBLIOGRAPHY_PATH.read_text(encoding="utf-8"), re.M))
    cited = {entry["source"] for row in registry["rules"].values() for entry in row.values() if entry["source"]}
    assert cited and cited <= keys, sorted(cited - keys)


# Literature cells whose source nobody has confirmed yet (null, rather than a citation no one
# checked). The expert review (PLAN_BEYOND_CI W1.4) fills them in; this ceiling only goes down.
UNSOURCED_CEILING = 110


def test_unsourced_literature_cells_only_decrease(registry: Any) -> None:
    unsourced = sorted(
        f"{rule}.{criterion}"
        for rule, row in registry["rules"].items()
        for criterion, entry in row.items()
        if entry["basis"] == "literature" and not entry["source"]
    )
    assert len(unsourced) <= UNSOURCED_CEILING, f"{len(unsourced)} unsourced cells: lower nothing, cite them"
