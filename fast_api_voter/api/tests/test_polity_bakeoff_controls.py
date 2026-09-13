"""Permutation and rendering controls (S2.5). See api/domain/polity/bakeoff_controls.py."""
from __future__ import annotations

import json
from typing import Any

import pytest

from api.domain.polity import bakeoff_controls as ctl
from api.domain.polity import bakeoff_scorecard as sc
from api.domain.polity.bakeoff_bank import BASE_CONTROL, Case, make_case
from api.domain.polity.bakeoff_report import family_summary
from api.tests.polity_bakeoff_fixtures import reference_bank


def _base(family: str) -> Case:
    return next(c for c in reference_bank().cases if c.family == family and c.labels.get("control") == BASE_CONTROL)


def _variant(family: str, control: str, t: float) -> Case:
    return next(c for c in reference_bank().cases if c.family == family and c.labels.get("control") == control and c.labels["t"] == t)


def test_permuted_stance_codes_move_the_table_and_every_rule_together() -> None:
    base = _base("response_sweep")
    permuted = ctl.permute_codes(base)
    assert "stance : 1 = COUNTER_MOBILIZATION\n2 = CONCESSION\n3 = DEFIANCE\n4 = SILENCE\n" in permuted.system_prompt
    assert "stance=2 (concession) exige au moins un ajustement ; stance=4 (silence) exige une liste vide" in permuted.system_prompt
    assert "stance=1 (counter_mobilization) exige motif 309" in permuted.system_prompt
    assert "301 = MANDATE_DEVIATION_HIGH" in permuted.system_prompt  # another field's codes are left alone
    assert permuted.user_prompt == base.user_prompt
    assert permuted.labels["codes"] == {"field": "stance", "to_canonical": {"2": 1, "3": 2, "4": 3, "1": 4}}
    assert permuted.labels["value"] == "2"  # CONCESSION's new code


def test_permuted_three_digit_codes_are_relabelled_wherever_they_appear() -> None:
    chamber = ctl.permute_codes(_base("chamber_poles"))
    assert "701 = DELIBERATIVE_SHIFT\n702 = SINCERE_POSITION" in chamber.system_prompt
    assert "tranche motif=702, shifts vide" in chamber.system_prompt
    assert (chamber.labels["value"], chamber.labels["value_char_offset"]) == ("1", 2)
    reaction = ctl.permute_codes(_base("reaction_scandal"))
    assert "motif == 401 (EVENT_PERSONALLY_IRRELEVANT)" in reaction.system_prompt and "utilise 403 avec" in reaction.system_prompt
    assert "value" not in reaction.labels or reaction.labels["value"] is None
    coalition = ctl.permute_codes(_base("coalition_diagonal"))
    assert "(action=2) ou refuse (action=1)" in coalition.system_prompt and "501 ou 502 si action=2" in coalition.system_prompt


def test_a_permutation_that_would_change_content_is_refused() -> None:
    base = _base("coalition_diagonal")
    no_table = make_case(family="f", decision_type="coalition_decision", system_prompt="action=1 only", user_prompt="{}",
                         think=False, budget=base.budget, unit_ids=(1,), labels=base.labels)
    with pytest.raises(ctl.UnsafeControlError, match="fewer than two"):
        ctl.permute_codes(no_table)
    unsorted_table = make_case(family="f", decision_type="coalition_decision", system_prompt="2 = LEAVE\n1 = JOIN",
                               user_prompt="{}", think=False, budget=base.budget, unit_ids=(1,), labels=base.labels)
    with pytest.raises(ctl.UnsafeControlError, match="does not invert"):
        ctl.permute_codes(unsorted_table)


def test_answers_to_permuted_codes_are_mapped_back_before_production_decodes_them() -> None:
    permuted = ctl.permute_codes(_base("coalition_diagonal"))
    answer = json.dumps({"decisions": [{"party_id": 1, "action": 2, "motif": 501}, {"party_id": 2, "action": 1, "motif": 504}, "odd"]})
    mapped = json.loads(ctl.canonical_content(permuted, answer))["decisions"]
    assert [d["action"] for d in mapped[:2]] == [1, 2] and mapped[2] == "odd"
    assert ctl.canonical_content(permuted, "not json") == "not json"
    assert ctl.canonical_content(permuted, '{"decisions": 3}') == '{"decisions": 3}'
    assert ctl.canonical_content(_base("coalition_diagonal"), answer) == answer


def test_every_rendering_keeps_every_value_of_every_contrast_case() -> None:
    for case in (c for c in reference_bank().cases if c.labels["kind"] == "contrast" and c.labels.get("control") == BASE_CONTROL):
        for name, (renderer, parser) in ctl.RENDERINGS.items():
            rendered = renderer(case.user_prompt)
            assert rendered != case.user_prompt and parser(rendered) == json.loads(case.user_prompt), (case.family, name)
    paths = ctl.render_paths('{"a":{"b":[1,2],"c":[{"d":null},{"e":{}}]},"f":[]}')
    assert paths == 'a.b = [1, 2]\na.c[0].d = null\na.c[1].e = {}\nf = []'
    assert ctl.parse_paths(paths) == {"a": {"b": [1, 2], "c": [{"d": None}, {"e": {}}]}, "f": []}
    assert ctl.parse_paths("x[1].y = 2\nx[0].y = 1") == {"x": [{"y": 1}, {"y": 2}]}
    assert ctl.parse_paths(ctl.render_paths('{"x":[{},{"a":1}]}')) == {"x": [{}, {"a": 1}]}


def test_adjacent_option_tables_are_sorted_separately() -> None:
    spec = ctl.CODE_FIELDS["coalition_decision"]
    text = "actions : 2 = LEAVE\n1 = JOIN\nagain : 2 = LEAVE\n1 = JOIN\nend"
    assert ctl.relabel_codes(text, {1: 1, 2: 2}, spec) == "actions : 1 = JOIN\n2 = LEAVE\nagain : 1 = JOIN\n2 = LEAVE\nend"


def test_a_rendering_that_loses_a_value_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(ctl.RENDERINGS, "rendering:lossy", (lambda prompt: "{}", json.loads))
    with pytest.raises(ctl.UnsafeControlError, match="does not keep every value"):
        ctl.render(_base("response_sweep"), "rendering:lossy")


def test_every_base_contrast_case_gets_its_controls_and_renumbered_cases_map_back_to_canonical_ids() -> None:
    bank = reference_bank()
    contrast_bases = [c for c in bank.cases if c.labels["kind"] == "contrast" and c.labels.get("control") == BASE_CONTROL]
    controls = {c.labels.get("control") for c in bank.cases if c.labels["kind"] == "contrast"}
    assert controls == {BASE_CONTROL, "renumbered", "codes", "rendering:indented", "rendering:paths"}
    assert len(ctl.controls_for(bank.cases)) == 3 * len(contrast_bases)  # renumbered ones are captures, not transformations

    base, renumbered = _variant("coalition_diagonal", BASE_CONTROL, 0.5), _variant("coalition_diagonal", "renumbered", 0.5)
    assert base.labels["units"] == [3] and renumbered.labels["units"] == [2]
    assert renumbered.labels["identity"] == {"0": 5, "1": 4, "2": 3, "3": 2, "4": 1}
    assert renumbered.unit_ids == (0, 1, 2, 3, 4)  # ids reversed: canonical responder 5, the farthest, is listed first
    chamber = _variant("chamber_poles", "renumbered", 1.0)
    assert chamber.unit_ids == (95, 96, 97, 98, 99) and chamber.labels["identity"]["95"] == 5


def _row_case(control: str, identity: dict[str, int] | None, t: float, unit: int) -> Case:
    labels: dict[str, Any] = {"kind": "contrast", "group": "g", "t": t, "control": control, "units": [unit], "field": "action", "value": "1"}
    if identity:
        labels["identity"] = identity
    return make_case(family="fam", decision_type="coalition_decision", system_prompt=control, user_prompt=f"{t}{unit}", think=False,
                     budget={"rule": "fixed", "max_tokens": 1}, unit_ids=(unit,), labels=labels)


def test_contrast_scoring_reports_each_control_and_its_agreement_with_production() -> None:
    cases = [_row_case(BASE_CONTROL, None, 0.0, 1), _row_case(BASE_CONTROL, None, 1.0, 1),
             _row_case("renumbered", {"4": 1}, 0.0, 4), _row_case("renumbered", {"4": 1}, 1.0, 4),
             _row_case("codes", None, 0.0, 1), _row_case("orphan", None, 0.0, 7)]
    answers = {cases[0].case_id: (1, 0.99), cases[1].case_id: (1, 0.97), cases[2].case_id: (1, 0.98), cases[3].case_id: (2, 0.2),
               cases[4].case_id: (2, None), cases[5].case_id: (1, None)}
    main = {cid: {"answers": {str(c.unit_ids[0]): a}, "probabilities": {str(c.unit_ids[0]): p} if p is not None else None}
            for c in cases for cid, (a, p) in answers.items() if cid == c.case_id}
    scored = sc.score_contrast(cases, main)
    assert scored["groups"]["g"]["flat"] is True
    renumbered = scored["controls"]["g"]["renumbered"]
    assert (renumbered["agreement_with_base"]["successes"], renumbered["agreement_with_base"]["trials"], renumbered["flat"]) == (1, 2, False)
    assert scored["controls"]["g"]["codes"]["agreement_with_base"]["successes"] == 0
    assert scored["controls"]["g"]["orphan"]["agreement_with_base"]["trials"] == 0

    summary = family_summary("fam", scored)
    assert "g controls: codes agrees 0/1 = 0.0%" in summary and "unread" in summary and "renumbered agrees 1/2 = 50.0%" in summary
    assert ", moves" in summary and "orphan agrees –" in summary
