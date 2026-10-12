"""ADR-026's measurement: does showing a president what the last elections would have given under other rules
change what they propose? Each sitting president of a finished run's final checkpoint takes the same turn many
times, at the exploration profile's temperature, with and without the stakes in their briefing; the amendments
they propose are counted by article, and a proposed voting method is checked against whom it would have elected.

Needs vLLM on config.llm.base_url. Usage (from fast_api_voter/):
    python scripts/check_amendment_stakes.py ~/Documents/Dev/polity-runs/phase12/runs --samples 20
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.accountability import current_sortition_members, is_term_limited, ticks_to_election  # noqa: E402
from api.domain.polity.agents import PRESIDENT_TURN, PresidentBriefing, decide_turn  # noqa: E402
from api.domain.polity.agents import president_system_prompt, president_user_prompt  # noqa: E402
from api.domain.polity.amendments import constitution_text, stakes_text  # noqa: E402
from api.domain.polity.ballot_and_aggregation import get_presidential_winner  # noqa: E402
from api.domain.polity.checkpoint import load_checkpoint  # noqa: E402
from api.domain.polity.citizen import Office  # noqa: E402
from api.domain.polity.constitution import in_force  # noqa: E402
from api.domain.polity.legislation import population_median  # noqa: E402
from api.domain.polity.legitimacy import approval  # noqa: E402
from api.domain.polity.llm_behavior_engine import ResponseContext  # noqa: E402
from api.domain.polity.llm_client import build_json_client  # noqa: E402
from api.domain.polity.simple_rules import candidate_label  # noqa: E402

WORKERS = 8


def _scenarios(root: Path) -> list[dict[str, Any]]:
    """Every run's final state: its president, the constitution in force with no proposal pending, and the last
    legislative vote (read from the journal: checkpoints from before ADR-026 do not keep it)."""
    import run_polity_flagship as flagship

    found = []
    for checkpoint_path in sorted(root.rglob("checkpoint.json")):
        state = load_checkpoint(checkpoint_path).state
        tick = load_checkpoint(checkpoint_path).tick
        president = next((c for c in state.citizens if c.office == Office.PRESIDENT), None)
        if president is None or state.legislature is None:
            continue
        results = [json.loads(line) for line in (checkpoint_path.parent / "events.jsonl").open()
                   if '"legislative_result"' in line]
        state.legislature.votes = {int(p): v for p, v in results[-1]["payload"]["votes"].items()} if results else None
        constitution = dataclasses.replace(state.constitution, pending=None) if state.constitution else None
        founding = flagship._flagship_config(
            engine="llm", years=8, population=len(state.citizens), seats=15, seed=1, output_dir=Path("/tmp/stakes-probe"),
            max_batch_replays=2, provider="vllm", workers=1, profile="exploration",
        )
        found.append(dict(run=checkpoint_path.parent.name, tick=tick, state=state, president=president,
                          constitution=constitution, config=in_force(founding, constitution)))
    return found


def _turn(scenario: dict[str, Any], with_stakes: bool, sample: int) -> dict[str, Any] | None:
    config, state, president, tick = scenario["config"], scenario["state"], scenario["president"], scenario["tick"]
    text = constitution_text(config, scenario["constitution"], len(current_sortition_members(state.citizens)))
    stakes = stakes_text(config, president, state.last_ballots, state.legislature) if with_stakes else None
    briefing = PresidentBriefing(
        tick=tick, ticks_per_year=config.run.ticks_per_year,
        context=ResponseContext(
            cid=president.citizen_id, legitimacy=president.legitimacy_capital, mandate_dev=0.0,
            street=president.street_pressure, lame_duck=is_term_limited(president, config.institutions.president_term_limit),
            ticks_left=ticks_to_election(tick, president.term_end_tick),
        ),
        approval=approval(state.citizens, president, config.vote, None), agenda_closed="a bill comes every 2 ticks",
        policy=state.legislature.policy, public_median=population_median(state.citizens), assembly_median=None,
        pledge=president.pledged_platform or president.issue_positions,
        stated=president.revealed_position or president.issue_positions,
        constitution=text + (f"\n{stakes}" if stakes else ""),
    )
    outcome = decide_turn(
        president, decision_type=PRESIDENT_TURN, system_prompt=president_system_prompt(president, config),
        user_prompt=president_user_prompt(briefing, ""), max_positions=config.mandate.max_response_shifts,
        agenda_open=False, config=config, client=build_json_client(config.llm, seed=10_000 * int(with_stakes) + sample),
    )
    amendment = getattr(outcome.turn, "amendment", None) if outcome.turn is not None else None
    if amendment is None:
        return None
    wins = None
    if amendment.article == "institutions.presidential_method" and state.last_ballots:
        wins = get_presidential_winner(state.last_ballots, str(amendment.value)) == candidate_label(president)
    return {"article": amendment.article, "value": amendment.value, "wins": wins}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path, help="a directory of finished runs (their checkpoint.json and events.jsonl)")
    parser.add_argument("--samples", type=int, default=20, help="turns per president per arm")
    args = parser.parse_args(argv)
    scenarios = _scenarios(args.root)
    print(f"{len(scenarios)} presidents: " + ", ".join(f"{s['run']} t{s['tick']} c{s['president'].citizen_id}" for s in scenarios))
    for with_stakes in (False, True):
        jobs = [(s, k) for s in scenarios for k in range(args.samples)]
        with ThreadPoolExecutor(WORKERS) as pool:
            proposals = list(pool.map(lambda job: _turn(job[0], with_stakes, job[1]), jobs))
        made = [p for p in proposals if p is not None]
        by_article = collections.Counter(p["article"].split(".")[-1] for p in made)
        methods = [p for p in made if p["wins"] is not None]
        print(f"\n{'with' if with_stakes else 'without'} the stakes: {len(made)} proposals in {len(jobs)} turns")
        print("  by article: " + ", ".join(f"{a} {n}" for a, n in by_article.most_common()))
        if methods:
            print(f"  voting-method proposals under which the president would have won: {sum(p['wins'] for p in methods)} of {len(methods)} "
                  f"({', '.join(sorted(str(p['value']) for p in methods))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
