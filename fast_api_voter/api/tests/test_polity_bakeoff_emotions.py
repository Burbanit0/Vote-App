"""ADR-012's prerequisite verdict, read exactly as pre-registered."""
from __future__ import annotations

from typing import Any

import pytest

from api.domain.polity import bakeoff_cases as bc
from api.domain.polity.bakeoff_bank import Case
from api.domain.polity.bakeoff_emotions import FELT, PLAIN, SWEEP, read_verdict, verdict_markdown
from api.domain.polity.codebook import PressureAct
from api.tests.polity_bakeoff_fixtures import reference_config

MOBILIZE, NOTHING = int(PressureAct.MOBILIZE), int(PressureAct.NOTHING)


@pytest.fixture(scope="module")
def bank_cases() -> list[Case]:
    return list(bc.generate_emotions_bank(reference_config()).cases)


def _session(cases: list[Case], *, felt_wrong: int = 0, felt_invalid: int = 0,
             sweep: dict[float, int] | None = None) -> dict[str, dict[str, Any]]:
    """Every truth case answered right, except `felt_wrong` emotions cases answered wrong and
    `felt_invalid` emotions cases invalid; the sweep mobilizes `sweep[anger]` citizens per level."""
    main: dict[str, dict[str, Any]] = {}
    felt_seen = 0
    mobilized: dict[float, int] = {}
    for case in cases:
        if case.family in (PLAIN, FELT):
            answers = {unit: (MOBILIZE if act else NOTHING) for unit, act in case.labels["truth"].items()}
            valid = True
            if case.family == FELT:
                if felt_seen < felt_invalid:
                    answers, valid = {}, False
                elif felt_seen < felt_invalid + felt_wrong:
                    answers = {unit: (NOTHING if act else MOBILIZE) for unit, act in case.labels["truth"].items()}
                felt_seen += 1
            main[case.case_id] = {"valid": valid, "answers": answers}
        elif case.family == SWEEP:
            anger = float(case.labels["t"])
            answers = {}
            for unit in case.labels["units"]:
                done = mobilized.get(anger, 0)
                act = MOBILIZE if done < (sweep or {}).get(anger, 0) else NOTHING
                mobilized[anger] = done + (act == MOBILIZE)
                answers[str(unit)] = act
            main[case.case_id] = {"valid": True, "answers": answers}
    return main


def test_equal_answers_are_accepted(bank_cases: list[Case]) -> None:
    verdict = read_verdict(bank_cases, _session(bank_cases))
    assert (verdict.valid_plain, verdict.valid_felt, verdict.correct_plain, verdict.correct_felt) == (24, 24, 24, 24)
    assert verdict.paired_citizens == 24 and not verdict.unpaired_citizens and verdict.accepted


def test_one_citizen_fewer_is_within_the_tolerance_and_two_are_not(bank_cases: list[Case]) -> None:
    one = read_verdict(bank_cases, _session(bank_cases, felt_wrong=1))
    assert (one.correct_felt, one.accuracy_holds, one.accepted) == (23, True, True)
    assert (one.mcnemar.first_only, one.mcnemar.second_only) == (1, 0)
    two = read_verdict(bank_cases, _session(bank_cases, felt_wrong=2))
    assert (two.correct_felt, two.accuracy_holds, two.accepted) == (22, False, False)


def test_fewer_valid_answers_with_the_fields_is_not_accepted(bank_cases: list[Case]) -> None:
    verdict = read_verdict(bank_cases, _session(bank_cases, felt_invalid=1))
    assert (verdict.valid_felt, verdict.validity_holds) == (23, False)
    assert not verdict.accepted  # its accuracy is within one, but validity alone refuses it


def test_the_sweep_is_reported_per_anger_level(bank_cases: list[Case]) -> None:
    verdict = read_verdict(bank_cases, _session(bank_cases, sweep={0.0: 0, 0.5: 2, 1.0: 4}))
    assert [(level.anger, level.answered, level.mobilize) for level in verdict.sweep] == [
        (0.0, 4, 0), (0.25, 4, 0), (0.5, 4, 2), (0.75, 4, 0), (1.0, 4, 4)]
    text = verdict_markdown(verdict, "control")
    assert "**Accepted.**" in text and "| 1 | 4 | 4 | 100% |" in text


def test_a_citizen_asked_in_only_one_family_is_reported_and_not_paired(bank_cases: list[Case]) -> None:
    dropped = next(case for case in bank_cases if case.family == FELT)
    unit = next(iter(dropped.labels["truth"]))
    cases = [case for case in bank_cases if case is not dropped]
    verdict = read_verdict(cases, _session(cases))
    assert (verdict.paired_citizens, verdict.unpaired_citizens) == (23, (unit,))
    assert f"Citizens asked in only one family, not paired: {unit}." in verdict_markdown(verdict, "control")
