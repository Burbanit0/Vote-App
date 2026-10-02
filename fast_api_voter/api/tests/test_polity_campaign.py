"""ADR-023 (roadmap 5.2): a nominee campaigns on one issue, and the citizens it reaches come to
weigh that issue more when they compare candidates."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.citizen import Citizen, generate_population
from api.domain.polity.config import PolityConfigError, load_config, validate_config
from api.domain.polity.llm_schemas import CAMPAIGNING_NOMINEE_TURN_JSON_SCHEMA, CampaigningNomineeTurn
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.salience import BASE, UNDECIDED, raise_salience, reached
from api.domain.polity.simple_rules import utility_ballot, weighted_distance
from api.tests.test_polity_agents import _AgentFakeClient, _agent_run_config, _turn

_CONFIG = load_config()


def _citizen(cid: int, positions: tuple[float, ...], priorities: tuple[float, ...], party: int | None = None) -> Citizen:
    return Citizen(
        citizen_id=cid, issue_positions=positions, issue_priorities=priorities, blank_threshold=0.3,
        ambition_score=0.5, party_affiliation=party, pledged_platform=positions,
    )


# ── the simplex move ──────────────────────────────────────────────────────

@pytest.mark.parametrize("step", [0.0, 0.01, 0.15, 0.5, 1.0])
def test_a_campaign_leaves_the_priorities_summing_to_one(step: float) -> None:
    # weighted_distance's bound (and so every blank_threshold comparison in the engine) rests on
    # this sum, so it is the one property the move must never break.
    for citizen in generate_population(_CONFIG.citizens, 20, 7):
        for issue in range(len(citizen.issue_priorities)):
            moved = raise_salience(citizen.issue_priorities, issue, step)
            assert sum(moved) == pytest.approx(1.0, abs=1e-9)
            assert all(weight >= 0.0 for weight in moved)


def test_the_issue_gains_what_the_others_give_up_and_zero_changes_nothing() -> None:
    before = (0.2, 0.3, 0.5)
    assert raise_salience(before, 0, 0.0) == before
    after = raise_salience(before, 0, 0.2)
    assert after[0] == pytest.approx(0.36)  # 0.2 + 0.2 * 0.8
    assert (after[1], after[2]) == (pytest.approx(0.24), pytest.approx(0.4))  # each scaled by 0.8
    assert raise_salience(before, 2, 1.0) == (0.0, 0.0, 1.0)


def test_a_campaign_moves_the_weight_not_the_opinion_so_it_can_serve_a_rival() -> None:
    # The voter is nearer the rival on issue 0 and nearer the nominee on issue 1. Campaigning on
    # issue 0 moves the voter toward the rival: the prompt says so, and the kernel must bear it out.
    voter = _citizen(0, (0.0, 0.0), (0.5, 0.5))
    nominee, rival = _citizen(1, (1.0, 0.0), (0.5, 0.5)), _citizen(2, (0.4, 1.0), (0.5, 0.5))
    before = weighted_distance(voter, nominee.issue_positions) - weighted_distance(voter, rival.issue_positions)
    voter.issue_priorities = raise_salience(voter.issue_priorities, 0, 0.5)
    after = weighted_distance(voter, nominee.issue_positions) - weighted_distance(voter, rival.issue_positions)
    assert after > before  # the nominee is now further ahead of the rival in distance, i.e. worse off
    assert voter.issue_positions == (0.0, 0.0)


# ── who hears it ──────────────────────────────────────────────────────────

def test_the_base_is_the_nominee_s_own_party_and_an_independent_reaches_nobody() -> None:
    nominee = _citizen(0, (0.5, 0.5), (0.5, 0.5), party=2)
    citizens = [nominee, _citizen(1, (0.5, 0.5), (0.5, 0.5), party=2), _citizen(2, (0.5, 0.5), (0.5, 0.5), party=3)]
    assert [c.citizen_id for c in reached(nominee, citizens, [nominee], _CONFIG.vote, BASE)] == [0, 1]
    independent = dataclasses.replace(nominee, party_affiliation=None)
    assert reached(independent, citizens, [independent], _CONFIG.vote, BASE) == []


def test_the_undecided_are_the_citizens_no_candidate_speaks_for() -> None:
    # Candidate at one corner: the citizen beside it has a ballot, the one far away votes blank.
    nominee = _citizen(0, (0.0, 0.0), (0.5, 0.5), party=1)
    near, far = _citizen(1, (0.05, 0.05), (0.5, 0.5)), _citizen(2, (1.0, 1.0), (0.5, 0.5))
    field = [nominee]
    assert utility_ballot(near, field, _CONFIG.vote) is not None
    heard = [c.citizen_id for c in reached(nominee, [near, far], field, _CONFIG.vote, UNDECIDED)]
    assert heard == [2]


# ── the rules ─────────────────────────────────────────────────────────────

def test_campaigning_needs_agent_nominees() -> None:
    with pytest.raises(PolityConfigError, match="campaign.salience_step"):
        validate_config(dataclasses.replace(_CONFIG, campaign=dataclasses.replace(_CONFIG.campaign, salience_step=0.2)))


def test_the_act_is_required_nullable_and_whole() -> None:
    # The only shape that survives both measurements: two required siblings had the model setting
    # one and leaving the other on 35% of calls (each costing the turn its retries), and an
    # optional nested object was filled once in 160 calls.
    fields: dict[str, Any] = dict(rationale="r", positions=[], bill=[], speech="s", note_to_self="", other_initiative="")
    assert "campaign" in CAMPAIGNING_NOMINEE_TURN_JSON_SCHEMA["required"]  # required, so always weighed
    assert CampaigningNomineeTurn(**fields, campaign=None).campaign is None  # nullable, so declining is sayable
    with pytest.raises(ValueError):
        CampaigningNomineeTurn(**fields)  # but not omittable: an omitted act is never weighed (OBS-031)
    plan = CampaigningNomineeTurn(**fields, campaign={"issue": 3, "audience": "base"}).campaign
    assert plan is not None and (plan.issue, plan.audience) == (3, BASE)
    assert "campaign" in CAMPAIGNING_NOMINEE_TURN_JSON_SCHEMA["properties"]
    for half in ({"issue": 3}, {"audience": "base"}, {"issue": -1, "audience": "base"}):
        with pytest.raises(ValueError):
            CampaigningNomineeTurn(**fields, campaign=half)


# ── a run ─────────────────────────────────────────────────────────────────

class _CampaigningClient(_AgentFakeClient):
    """Every nominee campaigns on issue 0 among its own base."""

    def complete_json(self, **kwargs: Any) -> str:
        if kwargs["json_schema"].get("title") != "CampaigningNomineeTurn":
            return str(super().complete_json(**kwargs))
        return json.dumps(_turn(campaign={"issue": 0, "audience": "base"}))


def test_a_run_journals_the_campaign_and_moves_the_citizens_it_reached(tmp_path: Path) -> None:
    config = _agent_run_config(tmp_path)
    config = dataclasses.replace(config, campaign=dataclasses.replace(config.campaign, salience_step=0.25))
    journal = run_simulation(config, run_id="campaign", llm_client=_CampaigningClient())
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    runs = [e for e in events if e["event_type"] == "campaign_run"]
    assert runs, "no campaign was journaled"
    assert {r["payload"]["issue"] for r in runs} == {0}
    assert {r["payload"]["audience"] for r in runs} == {"base"}
    assert {r["payload"]["step"] for r in runs} == {0.25}
    assert any(r["payload"]["citizens"] > 0 for r in runs)
    # The citizens who heard it keep a valid priority vector: the checkpoint is the proof it
    # survived the round trip as well as the move.
    saved = json.loads((journal.parent / "checkpoint.json").read_text())
    sums = [sum(c["issue_priorities"]) for c in saved["citizens"]]
    assert all(total == pytest.approx(1.0, abs=1e-9) for total in sums)
    assert max(c["issue_priorities"][0] for c in saved["citizens"]) > 0.25  # issue 0 really did rise
