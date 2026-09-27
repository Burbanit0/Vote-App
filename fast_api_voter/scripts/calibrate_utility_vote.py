"""S4.1's calibration: the utility vote's weights against ADR-011's pre-registered facts.

The grid and the selection rule were pre-registered in plan-polity-build-order.md §9 before
this script ran: partisanship and approval in {0, 0.05, 0.1} (party carryover 0.5),
turnout_cost in {0.005, 0.01, 0.02, 0.04}, valence 0; among the settings where all four
facts hold, the least partisanship + approval, then the mean turnout nearest 67.5%. The twin
is run_polity_flagship.py's full-mechanism config at population 100, deterministic, seeds
1-10, 8 years, every other Stage 4 mechanism at its shipped setting (off).

*Criterion changed before running, 2026-09-13.* ADR-011's fact 4 counted runs with one
president for all eight years, fewer than under the zero-weight arm. Since D6 set
`president_term_limit: 2`, an 8-year run holds elections at ticks 0, 16 and 32 and a
two-term president cannot stand at the third, so no arm can have such a run and the fact
could never hold. It is read instead as what OBS-001 measured alongside it: the share of
won elections won by the previous election's winner, lower than under the zero-weight arm.

What the journal does not carry is recorded by wrapping production functions for the run
(scripts/twin_runs.py): each election attempt's ballots, abstentions and judged incumbent
(`_presidential_ballots`), and each voter's first choice (`utility_ballot`).

Usage (from fast_api_voter/):
    python scripts/calibrate_utility_vote.py      # writes calibrate_utility_vote_results.{md,json}
"""
from __future__ import annotations

import dataclasses
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import PolityConfig  # noqa: E402
from api.domain.polity.simple_rules import BLANK_LABEL, citizen_id_from_label  # noqa: E402
from api.domain.polity.twin_calibration import (  # noqa: E402
    Arm,
    Election,
    FirstChoices,
    grid,
    select,
    utility_vote_arm,
    utility_vote_choice,
)
from twin_runs import SEEDS, recording, run_twin, twin_config  # noqa: E402

AXES = {"partisanship": (0.0, 0.05, 0.1), "approval": (0.0, 0.05, 0.1), "turnout_cost": (0.005, 0.01, 0.02, 0.04)}
FIXED = {"approval_party_carryover": 0.5, "valence": 0.0}
ZERO = {"partisanship": 0.0, "approval": 0.0, "turnout_cost": 0.0, "approval_party_carryover": 0.0, "valence": 0.0}
YEARS = 8
RESULTS = Path(__file__).resolve().parent / "calibrate_utility_vote_results"


def measure_run(seed: int, config: PolityConfig,
                run: Callable[[PolityConfig], list[dict[str, Any]]]) -> tuple[list[Election], FirstChoices]:
    """One run's election attempts and first choices, read by wrapping the engine while `run`
    runs it. The journal does not carry these; the twin runs the deterministic engine, and the
    LLM-path calibration (scripts/stage4_llm_utility_vote.py) replays a recorded call log."""
    attempts: list[dict[str, Any]] = []
    tally = [0, 0]

    def on_ballots(args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> None:
        citizens, nominees, _, _, tick, _, incumbent = args
        ballots, _abstained = result
        attempts.append({"tick": tick, "voters": len(citizens), "ballots": len(ballots), "incumbent": incumbent,
                         "standing": incumbent is not None and incumbent.citizen_id in {c.citizen_id for c in nominees}})

    def on_ballot(args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> None:
        voter, candidates = args[0], args[1]
        if result is None or voter.party_affiliation is None:
            return
        parties = {c.citizen_id: c.party_affiliation for c in candidates}
        if voter.party_affiliation not in parties.values():
            return
        tally[0] += 1
        tally[1] += result[0] != BLANK_LABEL and parties[citizen_id_from_label(result[0])] == voter.party_affiliation

    with recording("_presidential_ballots", on_ballots), recording("utility_ballot", on_ballot):
        events = run(config)
    winners = {e["tick"]: e["citizen_id"] for e in events if e["event_type"] == "elected"}
    elections = [
        Election(seed=seed, tick=a["tick"], voters=a["voters"], ballots=a["ballots"],
                 incumbent_id=a["incumbent"].citizen_id if a["incumbent"] else None,
                 incumbent_record=a["incumbent"].record if a["incumbent"] else None,
                 incumbent_standing=a["standing"], winner_id=winners.get(a["tick"]))
        for a in attempts
    ]
    return elections, FirstChoices(eligible=tally[0], own_party_first=tally[1])


def measure(vote: dict[str, float]) -> tuple[list[Election], FirstChoices]:
    elections: list[Election] = []
    choices = FirstChoices()
    for seed in SEEDS:
        config = twin_config(seed, YEARS)
        config = dataclasses.replace(config, vote=dataclasses.replace(config.vote, **vote))
        run_elections, run_choices = measure_run(seed, config, run_twin)
        elections += run_elections
        choices = choices + run_choices
    return elections, choices


def _setting(arm: Arm) -> str:
    return ", ".join(f"{k} {v}" for k, v in arm.setting.items() if k in AXES)


def markdown(zero: Arm, arms: list[Arm], chosen: Arm | None) -> str:
    fact_names = [fact.name for fact in zero.facts]
    lines = [
        "# S4.1 calibration: the utility vote (ADR-011)", "",
        "Generated by `scripts/calibrate_utility_vote.py`. Twin: full-mechanism config, population 100, "
        f"deterministic, seeds {SEEDS[0]}-{SEEDS[-1]}, {YEARS} years. Grid and selection pre-registered in "
        "`plan-polity-build-order.md` §9; fact 4 restated before running (see the script's docstring).", "",
        "## Verdict", "",
        (f"**Adopted:** {_setting(chosen)} (party carryover {FIXED['approval_party_carryover']})." if chosen
         else "**Nothing qualifies:** the weights stay at 0."),
        "",
        f"{sum(arm.qualifies for arm in arms)} of {len(arms)} settings meet all four facts.", "",
        "## Zero-weight arm", "",
        *[f"- {fact.name}: {fact.reading}" for fact in zero.facts], "",
        "## Every setting", "",
        "| setting | " + " | ".join(fact_names) + " | all |",
        "|---|" + "---|" * (len(fact_names) + 1),
    ]
    for arm in arms:
        cells = [f"{'✓' if fact.holds else '✗'} {fact.reading}" for fact in arm.facts]
        lines.append(f"| {_setting(arm)} | " + " | ".join(cells) + f" | {'✓' if arm.qualifies else '✗'} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    zero_elections, zero_choices = measure(ZERO)
    zero = utility_vote_arm(ZERO, zero_elections, zero_choices, zero_elections, zero_choices)
    arms = []
    for setting in grid(AXES):
        elections, choices = measure({**setting, **FIXED})
        arms.append(utility_vote_arm({**setting, **FIXED}, elections, choices, zero_elections, zero_choices))
        print(_setting(arms[-1]), "qualifies" if arms[-1].qualifies else "", flush=True)
    chosen = select(arms, utility_vote_choice)
    RESULTS.with_suffix(".md").write_text(markdown(zero, arms, chosen), encoding="utf-8")
    RESULTS.with_suffix(".json").write_text(json.dumps({
        "zero": dataclasses.asdict(zero), "arms": [dataclasses.asdict(arm) for arm in arms],
        "chosen": dataclasses.asdict(chosen) if chosen else None,
    }, indent=2), encoding="utf-8")
    print("chosen:", _setting(chosen) if chosen else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
