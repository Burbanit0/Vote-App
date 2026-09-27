"""The bake-off case bank (S2.2). See api/domain/polity/bakeoff_cases.py."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from api.domain.polity import bakeoff_bank as bb
from api.domain.polity import bakeoff_cases as bc
from api.domain.polity import bakeoff_runner as br
from api.domain.polity.citizen import generate_population
from api.domain.polity.config import PolityConfig
from api.domain.polity.llm_behavior_engine import (
    _VLLM_MAX_TOKENS_SAFETY_MARGIN,
    cast_votes,
    compute_max_tokens,
    decide_campaign_positioning,
    decide_candidacies,
)
from api.domain.polity.llm_call_log import request_sha256
from api.domain.polity.llm_client import LlmResponseError
from api.tests.polity_bakeoff_fixtures import reference_bank, reference_config
from api.tests.polity_golden import RecordingClient
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient

COMMITTED_BANK = Path(__file__).resolve().parents[2] / "scripts" / "bakeoff" / "case_bank.jsonl"


class _FixedTokenCount:
    def count_prompt_tokens(self, **_: object) -> int:
        return 1000


def _without_adopted_arms(config: PolityConfig) -> PolityConfig:
    """Production with S1.2's grammar and S1.3's budget off: the request a bank case poses.
    Both were adopted as defaults on 2026-09-16, and both are arms the bake-off adds to a case
    rather than part of it -- which is what keeps the bank comparable across sessions."""
    return dataclasses.replace(config, llm=dataclasses.replace(
        config.llm, vote_cast_grammar_invariants=False, thinking_token_budget=None))


def _case_hashes(cases: list[bb.Case], client: object) -> list[str]:
    config = reference_config()
    return [
        request_sha256(system_prompt=c.system_prompt, user_prompt=c.user_prompt, json_schema=bb.SCHEMAS[c.decision_type],
                       max_tokens=bc.resolve_max_tokens(c, client, config), think=c.think)  # type: ignore[arg-type]
        for c in cases
    ]


def test_the_bank_is_the_same_every_time_it_is_generated_and_survives_a_round_trip(tmp_path: Path) -> None:
    bank = reference_bank()
    assert bank.families() == sorted(bc.FAMILIES)
    assert {c.decision_type for c in bank.cases} == set(bb.SCHEMAS)
    assert bc.generate_bank(reference_config()).content_sha256 == bank.content_sha256

    bb.write_bank(bank, tmp_path / "bank.jsonl")
    assert bb.read_bank(tmp_path / "bank.jsonl") == bank


def test_a_bank_edited_after_it_was_frozen_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "bank.jsonl"
    bb.write_bank(reference_bank(), path)
    lines = path.read_text().splitlines()
    case = json.loads(lines[1])
    case["user_prompt"] += " "
    path.write_text("\n".join([lines[0], json.dumps(case), *lines[2:]]) + "\n")
    with pytest.raises(bb.BankIntegrityError, match="does not match the frozen"):
        bb.read_bank(path)


def test_the_committed_bank_is_intact_and_covers_every_family_and_decision_type() -> None:
    bank = bb.read_bank(COMMITTED_BANK)
    assert bank.families() == sorted(bc.FAMILIES)
    assert {c.decision_type for c in bank.cases} == set(bb.SCHEMAS)
    assert bank.reference == {"provider": "vllm", "model": "qwen3:8b", "seed": 42, "max_batch_size": 25}


def test_captured_requests_are_byte_identical_to_what_production_sends() -> None:
    """Candidacy (a fixed budget), vote_cast (a probed budget) and campaign positioning (a
    profile allowance): production run with an answering client, its adopted request arms
    off, sends exactly the cases."""
    config = _without_adopted_arms(reference_config())
    fake = _ElectingFakeLlmClient()
    bank = reference_bank()

    recorder = RecordingClient(fake)
    decide_candidacies(generate_population(config.citizens, 500, config.run.seed), config, recorder)
    assert [h for _, h in recorder.requests] == _case_hashes([c for c in bank.cases if c.family == "candidacy_p500"], fake)

    voters, nominees, truth = bc._vote_scenario(config)
    recorder = RecordingClient(fake)
    cast_votes(bc._balanced(voters, truth, per_class=8, skip=0), nominees, config, recorder)
    assert [h for _, h in recorder.requests] == _case_hashes([c for c in bank.cases if c.family == bb.LOGPROB_GATE_FAMILY], fake)

    positioning = [c for c in bank.cases if c.family == "positioning_poles"]
    citizens = generate_population(config.citizens, 300, config.run.seed)
    parties = bc._with_parties(config, citizens)
    nominee_ids = {int(cid) for cid in positioning[0].labels["units"]}
    recorder = RecordingClient(fake)
    decide_campaign_positioning([c for c in citizens if c.citizen_id in nominee_ids], citizens, {p.party_id: p for p in parties}, config, recorder)
    assert [h for _, h in recorder.requests] == _case_hashes(positioning[:1], fake)


def test_shipped_vote_requests_are_the_bank_cases_with_exactly_the_two_adopted_arms() -> None:
    """S1.2 and S1.3 adopted two bake-off request arms as production defaults. A shipped
    vote_cast request is therefore the bank's case with the `vote_grammar` arm's schema and the
    `thinking_budget_2048` arm's field applied -- the same functions the sessions ran, so what
    production sends is exactly what was measured, and nothing besides."""
    config = reference_config()
    assert (config.llm.vote_cast_grammar_invariants, config.llm.thinking_token_budget) == (True, 2048)
    fake = _ElectingFakeLlmClient()
    voters, nominees, truth = bc._vote_scenario(config)
    recorder = RecordingClient(fake)
    cast_votes(bc._balanced(voters, truth, per_class=8, skip=0), nominees, config, recorder)

    budget = br.ARMS["thinking_budget_2048"].request
    grammar = br.ARMS["vote_grammar"].schema
    assert budget is not None and grammar is not None
    expected = [
        request_sha256(system_prompt=c.system_prompt, user_prompt=c.user_prompt,
                       json_schema=grammar(c, bb.SCHEMAS[c.decision_type]),
                       max_tokens=bc.resolve_max_tokens(c, fake, config), think=c.think,  # type: ignore[arg-type]
                       extra_body=budget(c)["extra_body"])
        for c in reference_bank().cases if c.family == bb.LOGPROB_GATE_FAMILY
    ]
    assert [h for _, h in recorder.requests] == expected


def test_budget_rules_follow_how_production_sized_the_request() -> None:
    config = reference_config()
    request = bc.CapturedRequest("vote_cast", "s", "u", max_tokens=99, think=True, unit_ids=(1, 2, 3), probed=True)
    assert bc.budget_rule(request) == {"rule": "probe", "chunk_size": 3, "allowance": "vote_think_allowance"}
    positioning = dataclasses.replace(request, decision_type="campaign_positioning", probed=False)
    assert bc.budget_rule(positioning) == {"rule": "allowance", "chunk_size": 3, "allowance": "positioning_think_allowance"}
    fixed = dataclasses.replace(request, decision_type="candidacy_considered", probed=False)
    assert bc.budget_rule(fixed) == {"rule": "fixed", "max_tokens": 99}

    def case_for(budget: dict[str, object]) -> bb.Case:
        return bb.make_case(family="f", decision_type="vote_cast", system_prompt="s", user_prompt="u", think=True,
                            budget=budget, unit_ids=(1, 2, 3), labels={"kind": "truth", "truth": {}})

    client = _FixedTokenCount()
    assert bc.resolve_max_tokens(case_for(bc.budget_rule(fixed)), client, config) == 99  # type: ignore[arg-type]
    assert bc.resolve_max_tokens(case_for(bc.budget_rule(positioning)), client, config) == compute_max_tokens(3) + 8000  # type: ignore[arg-type]
    assert bc.resolve_max_tokens(case_for(bc.budget_rule(request)), client, config) == 16384 - 1000 - _VLLM_MAX_TOKENS_SAFETY_MARGIN  # type: ignore[arg-type]


def test_the_capturing_client_keeps_first_attempts_and_fails_every_call() -> None:
    client = bc.CapturingClient()
    for temperature in (None, 0.3):
        with pytest.raises(LlmResponseError):
            client.complete_json(system_prompt="s", user_prompt="u", json_schema=bb.SCHEMAS["vote_cast"], max_tokens=10, temperature=temperature)
    assert [(r.decision_type, r.unit_ids, r.probed) for r in client.requests] == [("vote_cast", (), False)]


def test_the_vote_scenario_refuses_a_sample_its_electorate_cannot_fill() -> None:
    voters, _, truth = bc._vote_scenario(reference_config())
    with pytest.raises(ValueError, match="too few voters"):
        bc._balanced(voters, truth, per_class=len(voters), skip=0)


def test_each_family_labels_its_cases_for_scoring() -> None:
    bank = reference_bank()
    by_family = {family: [c for c in bank.cases if c.family == family] for family in bank.families()}
    assert sum(len(c.unit_ids) for c in by_family["candidacy_p500"]) == 500
    assert sum(len(c.labels["truth"]) for c in by_family[bb.LOGPROB_GATE_FAMILY]) == 16
    gate_truth = [v for c in by_family[bb.LOGPROB_GATE_FAMILY] for v in c.labels["truth"].values()]
    assert gate_truth.count("blank") == 8
    base_sweep = [c for c in by_family["response_sweep"] if c.labels["control"] == bb.BASE_CONTROL]
    assert sorted(c.labels["t"] for c in base_sweep) == [i / 8 for i in range(9)]
    assert all(c.labels["match"] == "acts" for c in by_family["pressure_act"])
    assert sorted(v for c in by_family["pressure_act"] for v in c.labels["truth"].values()) == [False] * 12 + [True] * 12
    assert {c.budget["rule"] for c in by_family["chamber_poles"]} == {"probe"}


def test_a_nomination_pair_lists_the_same_citizens_in_reverse_order() -> None:
    pair = [c for c in reference_bank().cases if c.family == "nomination_permutation" and c.labels["pair"] == "seed42"]
    original, renumbered = sorted(pair, key=lambda c: c.labels["rendering"])
    assert (original.labels["rendering"], renumbered.labels["rendering"]) == ("original", "renumbered")

    def in_listed_order(listed: dict[str, int]) -> list[int]:
        return [listed[position] for position in sorted(listed, key=int)]

    assert original.labels["listed"].keys() == renumbered.labels["listed"].keys()
    for party, listed in original.labels["listed"].items():
        assert in_listed_order(renumbered.labels["listed"][party]) == in_listed_order(listed)[::-1]


def test_drift_names_the_cases_production_no_longer_renders() -> None:
    bank = reference_bank()
    changed = bb.make_case(**{**{k: v for k, v in dataclasses.asdict(bank.cases[0]).items() if k != "case_id"}, "user_prompt": "changed"})
    current = dataclasses.replace(bank, cases=(changed, *bank.cases[1:]))
    assert bc.drift(bank, current) == {"no_longer_rendered": [bank.cases[0].case_id], "newly_rendered": [changed.case_id]}
    assert bc.drift(bank, bank) == {"no_longer_rendered": [], "newly_rendered": []}


# ── ADR-012's prerequisite: a bank whose pressure cases carry emotions ────────

def test_the_emotions_bank_leaves_pressure_act_exactly_as_the_frozen_bank_renders_it() -> None:
    """One session answers both halves of the comparison only if `pressure_act` is the same case,
    byte for byte, in both banks."""
    emotions = bc.generate_emotions_bank(reference_config())
    assert {case.family for case in emotions.cases} == set(bc.EMOTION_FAMILIES)
    frozen = {c.case_id for c in reference_bank().cases if c.family == "pressure_act"}
    assert {c.case_id for c in emotions.cases if c.family == "pressure_act"} == frozen and len(frozen) == 24
    assert bc.generate_emotions_bank(reference_config()).content_sha256 == emotions.content_sha256  # deterministic


def test_the_emotion_fields_are_the_only_difference_and_the_truth_is_the_same() -> None:
    cases = bc.generate_emotions_bank(reference_config()).cases
    plain = [c for c in cases if c.family == "pressure_act"]
    felt = [c for c in cases if c.family == "pressure_act_emotions"]
    assert len(felt) == len(plain) == 24
    assert all("ctx.anger" in c.user_prompt or '"anger"' in c.user_prompt for c in felt)
    assert not any("anger" in c.user_prompt for c in plain)
    assert [c.labels["truth"] for c in felt] == [c.labels["truth"] for c in plain]


def test_the_anger_sweep_asks_the_same_citizens_at_each_level() -> None:
    sweep = [c for c in bc.generate_emotions_bank(reference_config()).cases if c.family == "pressure_anger_sweep"]
    assert sorted({c.labels["t"] for c in sweep}) == list(bc.ANGER_LEVELS)
    units_by_level = {t: sorted(u for c in sweep if c.labels["t"] == t for u in c.labels["units"]) for t in bc.ANGER_LEVELS}
    assert len({tuple(units) for units in units_by_level.values()}) == 1  # the same four citizens throughout
    assert all(len(units) == 4 for units in units_by_level.values())
    assert all(c.labels["kind"] == "contrast" and c.labels["field"] == "act" for c in sweep)

