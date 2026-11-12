"""The behaviour catalogue and its tests stay in step (Phase 13b).

docs/spec/behaviors.md numbers the invariants the polity simulator promises; a test
that checks one carries `@pytest.mark.behavior("ELE-01", ...)`. This reads both sides
without importing any test module (the markers are found in the AST) and fails on an
invariant no test checks, a marker naming an ID the catalogue doesn't have, or an ID
listed twice. It only proves a test is linked to each invariant, not what it asserts:
the catalogue is held for the owner's review so the link is read by a person.
"""
from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
CATALOGUE = REPO / "docs" / "spec" / "behaviors.md"
TESTS = Path(__file__).resolve().parent
_ID = re.compile(r"[A-Z]{3}-\d{2}")


def catalogue_rows(text: str) -> tuple[list[str], list[str]]:
    """(IDs, malformed first cells) over every table row of the catalogue.

    Every table in behaviors.md lists invariants, so a row whose first cell is not
    a well-formed ID (`ELE-01`) is reported rather than skipped: a skipped row would
    need no test and pass unseen."""
    ids: list[str] = []
    malformed: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip()
        if cell == "ID" or set(cell) <= {"-", ":"}:
            continue  # header and separator rows
        (ids if _ID.fullmatch(cell) else malformed).append(cell)
    return ids, malformed


def catalogue_ids(text: str) -> list[str]:
    return catalogue_rows(text)[0]


def _is_behavior_mark(node: ast.AST) -> bool:
    # pytest.mark.behavior(...) as a decorator call.
    f = node.func if isinstance(node, ast.Call) else None
    return (
        isinstance(f, ast.Attribute)
        and f.attr == "behavior"
        and isinstance(f.value, ast.Attribute)
        and f.value.attr == "mark"
    )


def marked_tests(source: str) -> dict[str, list[str]]:
    """{test name: [IDs]} for every test function decorated with a behavior mark.

    Only a decorator on a test function counts. A behavior mark anywhere else
    (`pytestmark = ...`, a class decorator), or one with no ID or a non-literal ID,
    raises: pytest would apply it, but this check could not see what it links."""
    tree = ast.parse(source)
    found: dict[str, list[str]] = {}
    placed: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if _is_behavior_mark(dec):
                    assert isinstance(dec, ast.Call)
                    ids = [a.value for a in dec.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                    if not dec.args or len(ids) != len(dec.args):
                        raise ValueError(f"{node.name}: behavior() takes one or more literal string IDs")
                    placed.add(id(dec))
                    found.setdefault(node.name, []).extend(ids)
    stray = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and _is_behavior_mark(n) and id(n) not in placed]
    if stray:
        raise ValueError(f"behavior() used other than as a test function's decorator, line(s) {stray}")
    return found


def _all_marks() -> dict[str, list[str]]:
    """{ID: ["file::test", ...]} over the whole test directory."""
    by_id: dict[str, list[str]] = {}
    for path in sorted(TESTS.glob("test_*.py")):
        for test, ids in marked_tests(path.read_text(encoding="utf-8")).items():
            for i in ids:
                by_id.setdefault(i, []).append(f"{path.name}::{test}")
    return by_id


def test_the_catalogue_lists_invariants_once_each() -> None:
    ids, malformed = catalogue_rows(CATALOGUE.read_text(encoding="utf-8"))
    assert not malformed, f"table rows whose first cell is not an ID like ELE-01: {malformed}"
    assert ids, "no `| XXX-NN |` rows found in docs/spec/behaviors.md -- has its table format changed?"
    dupes = sorted(i for i, n in Counter(ids).items() if n > 1)
    assert not dupes, f"listed more than once in behaviors.md: {dupes}"


def test_every_invariant_has_a_test() -> None:
    marks = _all_marks()
    untested = [i for i in catalogue_ids(CATALOGUE.read_text(encoding="utf-8")) if i not in marks]
    assert not untested, (
        f"no test is marked @pytest.mark.behavior(...) for {untested}: mark the test that "
        "checks it, or move it to the catalogue's Candidates section"
    )


def test_every_marker_names_a_catalogued_invariant() -> None:
    known = set(catalogue_ids(CATALOGUE.read_text(encoding="utf-8")))
    unknown = {i: where for i, where in _all_marks().items() if i not in known}
    assert not unknown, f"behavior() names IDs that docs/spec/behaviors.md doesn't list: {unknown}"


def test_the_parsers_read_rows_and_marks() -> None:
    # The checks above are only as good as these two readers.
    table = "| ID | Invariant |\n|---|---|\n| ELE-01 | a |\n| CIT-100 | b |\n| CIT-10 | c |\n- ELE-99 candidate"
    assert catalogue_rows(table) == (["ELE-01", "CIT-10"], ["CIT-100"])
    source = (
        "import pytest\n"
        "@pytest.mark.behavior('ELE-01', 'DET-02')\n"
        "@pytest.mark.parametrize('x', [1])\n"
        "def test_a(x): pass\n"
        "def test_unmarked(): pass\n"
        "class TestK:\n"
        "    @pytest.mark.behavior('JRN-01')\n"
        "    async def test_b(self): pass\n"
    )
    assert marked_tests(source) == {"test_a": ["ELE-01", "DET-02"], "test_b": ["JRN-01"]}
    for bad in (
        "import pytest\n@pytest.mark.behavior()\ndef test_x(): pass\n",
        "import pytest\nID = 'ELE-01'\n@pytest.mark.behavior(ID)\ndef test_x(): pass\n",
        "import pytest\npytestmark = pytest.mark.behavior('ELE-01')\n",
        "import pytest\n@pytest.mark.behavior('ELE-01')\nclass TestK:\n    def test_x(self): pass\n",
    ):
        with pytest.raises(ValueError, match=r"behavior\(\)"):
            marked_tests(bad)
