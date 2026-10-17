"""scripts/check_nomination_position_bias.py: OBS-013's reading of a nomination_permutation session."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from api.domain.polity.bakeoff_bank import CaseBank, write_bank
from api.tests.polity_bakeoff_fixtures import reference_bank

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_nomination_position_bias.py"


@pytest.fixture(scope="module")
def check() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_nomination_position_bias", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _session(tmp_path: Path, pick: str) -> tuple[Path, Path]:
    """The bank's nomination cases, answered by a model that always picks the `last` or the `first` listed."""
    cases = [c for c in reference_bank().cases if c.family == "nomination_permutation"]
    bank_path = tmp_path / "bank.jsonl"
    write_bank(CaseBank(reference=reference_bank().reference, cases=tuple(cases)), bank_path)
    session = tmp_path / "session"
    session.mkdir()
    rows = []
    for case in cases:
        answers = {party: (len(listed) if pick == "last" else 1) for party, listed in case.labels["listed"].items()}
        rows.append({"case_id": case.case_id, "pass": "main", "valid": True, "answers": answers})
    (session / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return bank_path, session


def test_the_exact_tail_of_a_uniform_pick_is_a_poisson_binomial(check: ModuleType) -> None:
    assert check.upper_tail([2, 2], 2) == (1.0, pytest.approx(0.25))
    assert check.upper_tail([2, 2], 1)[1] == pytest.approx(0.75)
    assert check.upper_tail([2, 4], 2) == (0.75, pytest.approx(0.125))
    assert check.upper_tail([3, 3, 3], 0)[1] == pytest.approx(1.0)


def test_a_model_that_always_picks_the_last_listed_follows_the_position_not_the_candidate(check: ModuleType, tmp_path: Path) -> None:
    units = check.read_units(*_session(tmp_path, "last"))
    assert units and all(u["pick"] == (u["size"], u["size"]) for u in units)
    assert not any(u["same"] for u in units if u["size"] > 1)  # reversing the list moved the candidate it names


def test_a_model_that_picks_the_same_candidate_in_both_orders_is_seen_to_follow_it(check: ModuleType, tmp_path: Path) -> None:
    bank_path, session = _session(tmp_path, "first")
    rows = [json.loads(line) for line in (session / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    cases = {c.case_id: c for c in reference_bank().cases if c.family == "nomination_permutation"}
    by_pair: dict[str, dict[str, dict[str, object]]] = {}
    for row in rows:
        case = cases[row["case_id"]]
        by_pair.setdefault(case.labels["pair"], {})[case.labels["rendering"]] = row
    for pair in by_pair.values():  # in the reversed rendering, name the citizen the original rendering picked
        original, reversed_ = cases[str(pair["original"]["case_id"])], cases[str(pair["renumbered"]["case_id"])]
        for party, listed in original.labels["listed"].items():
            citizen = listed["1"]
            pair["renumbered"]["answers"][party] = next(int(p) for p, c in reversed_.labels["listed"][party].items() if c == citizen)  # type: ignore[index]
    (session / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    units = check.read_units(bank_path, session)
    assert units and all(u["same"] for u in units)


def test_the_report_prints_the_three_strata(check: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bank_path, session = _session(tmp_path, "last")
    assert check.main([str(bank_path), str(session)]) == 0
    out = capsys.readouterr().out
    assert "all:" in out and "last listed:" in out and "same citizen in both orders:" in out
    assert check.main([]) == 2  # no arguments: the usage text
