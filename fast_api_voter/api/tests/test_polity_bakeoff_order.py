"""The rule that picks each decision's field order from order-bank sessions (ADR-030).
See api/domain/polity/bakeoff_order.py."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from api.domain.polity.bakeoff_bank import Case, CaseBank, make_case
from api.domain.polity.bakeoff_order import decide, proposed_table, table_order
from api.domain.polity.bakeoff_scorecard import Session

N = 40
DECLARED = {"PressureDecision": ("cid", "target", "act", "motif")}
CHOSEN = {"PressureDecision": ("cid", "motif", "act", "target")}


def _bank() -> CaseBank:
    """40 one-citizen pressure cases, half who should act and half who should not."""
    return CaseBank(reference={}, cases=tuple(
        make_case(family="pressure_act_wide", decision_type="pressure_action", system_prompt="s", user_prompt=f"u{i}",
                  think=False, budget={"rule": "fixed", "max_tokens": 8}, unit_ids=[i],
                  labels={"kind": "truth", "truth": {str(i): i % 2 == 0}, "match": "acts"})
        for i in range(N)
    ))


def _session(label: str, act: Callable[[int], int]) -> Session:
    def result(case: Case) -> dict[str, Any]:
        unit = case.unit_ids[0]
        return {"case_id": case.case_id, "pass": "main", "answers": {str(unit): act(unit)}, "valid": True,
                "content_sha256": f"{label}-{act(unit)}", "error": None}
    return Session(label=label, metadata={}, gates={}, results=[result(c) for c in _bank().cases])


def _pressure(verdicts: list[Any]) -> Any:
    return next(v for v in verdicts if v.title == "PressureDecision")


def _half_right(unit: int) -> int:
    """Acts only for the first half, whatever the truth: right on 20 of 40, and a mix of answers."""
    return 3 if unit < N // 2 else 0


def test_a_candidate_that_beats_both_controls_replaces_the_current_order() -> None:
    controls = (_session("control-a", _half_right), _session("control-b", _half_right))
    right = _session("right", lambda unit: 3 if unit % 2 == 0 else 0)  # right on all 40
    verdicts = decide(_bank(), controls, {"order_mdx": (CHOSEN, right), "same": (DECLARED, controls[0])}, {})
    pressure = _pressure(verdicts)
    assert pressure.primary == "pressure_act_wide" and pressure.noise == 0.0
    assert pressure.chosen == CHOSEN["PressureDecision"] and pressure.reason == "order_mdx beats the control"
    assert {c.rule: c.wins for c in pressure.candidates} == {"order_mdx": True, "same": False}
    assert proposed_table(verdicts) == CHOSEN  # the other decision types are not in this bank: unchanged
    assert {v.reason for v in verdicts if v.title != "PressureDecision"} == {"not in the bank"}


def test_without_a_significant_gain_the_current_order_stays() -> None:
    controls = (_session("control-a", _half_right), _session("control-b", _half_right))
    slightly = _session("slightly", lambda unit: 3 if unit < N // 2 or unit in (20, 22) else 0)  # 22 of 40
    pressure = _pressure(decide(_bank(), controls, {"order_mdx": (CHOSEN, slightly)}, DECLARED))
    assert pressure.chosen == pressure.current == DECLARED["PressureDecision"]
    assert pressure.reason == "no candidate beats the control"


def test_a_gain_that_comes_from_collapsing_onto_one_answer_is_refused() -> None:
    wrong = (lambda unit: 0 if unit % 2 == 0 else 3)  # wrong on all 40, with a mix of answers
    controls = (_session("control-a", wrong), _session("control-b", wrong))
    always = _session("always", lambda unit: 3)  # right on the 20 who should act, by acting for everyone
    pressure = _pressure(decide(_bank(), controls, {"order_mdx": (CHOSEN, always)}, {}))
    assert pressure.candidates[0].failures == ("collapsed onto one answer",)
    assert pressure.chosen == table_order({}, "PressureDecision") == ("act", "cid", "motif", "target")


def test_a_measure_the_two_controls_disagree_on_is_too_noisy_to_decide() -> None:
    controls = (_session("control-a", _half_right), _session("control-b", lambda unit: 3 if unit < 30 else 0))
    right = _session("right", lambda unit: 3 if unit % 2 == 0 else 0)
    pressure = _pressure(decide(_bank(), controls, {"order_mdx": (CHOSEN, right)}, {}))
    assert pressure.noise == 0.25 and pressure.reason == "too noisy to tell" and pressure.candidates == ()
    assert pressure.chosen == ("act", "cid", "motif", "target")


def test_a_candidate_sending_the_current_order_is_not_a_candidate() -> None:
    controls = (_session("control-a", _half_right), _session("control-b", _half_right))
    pressure = _pressure(decide(_bank(), controls, {"same": (DECLARED, controls[0])}, DECLARED))
    assert pressure.candidates == () and pressure.chosen == DECLARED["PressureDecision"]


def _chamber_bank() -> CaseBank:
    """40 chamber cases without ground truth: the decision type's primary measure is its validity."""
    return CaseBank(reference={}, cases=tuple(
        make_case(family="chamber_poles", decision_type="chamber_deliberation", system_prompt="s", user_prompt=f"c{i}",
                  think=True, budget={"rule": "fixed", "max_tokens": 8}, unit_ids=[i], labels={"kind": "contrast"})
        for i in range(N)
    ))


def _validity_session(label: str, valid: Callable[[int], bool]) -> Session:
    return Session(label=label, metadata={}, gates={}, results=[
        {"case_id": c.case_id, "pass": "main", "answers": {str(c.unit_ids[0]): 701}, "valid": valid(c.unit_ids[0]),
         "content_sha256": label, "error": None} for c in _chamber_bank().cases])


def test_without_ground_truth_validity_decides_and_a_clear_gain_in_it_wins() -> None:
    half = (lambda unit: unit < N // 2)
    controls = (_validity_session("control-a", half), _validity_session("control-b", half))
    table = {"ChamberDecision": ("cid", "shifts", "motif")}  # alphabetical is cid, motif, shifts
    chamber = next(v for v in decide(_chamber_bank(), controls, {"order_mdx": (table, _validity_session("all", lambda u: True))}, {})
                   if v.title == "ChamberDecision")
    assert chamber.primary == "validity" and chamber.noise == 0.0
    assert chamber.chosen == ("cid", "shifts", "motif") and chamber.candidates[0].wins


def test_a_gain_in_accuracy_that_costs_validity_is_refused() -> None:
    controls = (_session("control-a", _half_right), _session("control-b", _half_right))
    right = _session("right", lambda unit: 3 if unit % 2 == 0 else 0)
    invalid = Session(label="invalid", metadata={}, gates={},
                      results=[{**r, "valid": int(r["case_id"], 16) % 4 != 0} for r in right.results])
    pressure = _pressure(decide(_bank(), controls, {"order_mdx": (CHOSEN, invalid)}, {}))
    assert "validity significantly worse" in pressure.candidates[0].failures and not pressure.candidates[0].wins
