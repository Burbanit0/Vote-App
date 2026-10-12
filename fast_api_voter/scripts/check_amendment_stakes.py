"""ADR-026/027's measurement: does showing a president what the rules would give them -- today's ballots under each
voting method, the last legislative votes under each seat rule --
change what they propose? Each sitting president of a finished run's final checkpoint takes the same turn many
times, at the exploration profile's temperature, with and without the stakes in their briefing; the amendments
they propose are counted by article, and a proposed voting method is checked against whom today's ballots elect.

Needs vLLM on config.llm.base_url. Usage (from fast_api_voter/):
    python scripts/check_amendment_stakes.py ~/Documents/Dev/polity-runs/phase11 ~/Documents/Dev/polity-runs/phase12/runs --samples 2

A president's answer barely varies between samples at temperature 0.6 (40 of 40 alike, then 0 of 40 in a second
run of the same turns), so presidents, not samples, are the unit: give it many runs, few samples.
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
from api.domain.polity.agents import HIGH_AMBITION, LOW_AMBITION, PRESIDENT_TURN, PresidentBriefing, decide_turn  # noqa: E402
from api.domain.polity.agents import president_system_prompt, president_user_prompt  # noqa: E402
from api.domain.polity.amendments import constitution_text, stakes_text  # noqa: E402
from api.domain.polity.ballot_and_aggregation import get_presidential_winner  # noqa: E402
from api.domain.polity.checkpoint import load_checkpoint  # noqa: E402
from api.domain.polity.citizen import Office  # noqa: E402
from api.domain.polity.config import ARTICLES  # noqa: E402
from api.domain.polity.constitution import in_force  # noqa: E402
from api.domain.polity.legislation import population_median  # noqa: E402
from api.domain.polity.legitimacy import approval  # noqa: E402
from api.domain.polity.llm_behavior_engine import ResponseContext  # noqa: E402
from api.domain.polity.llm_client import build_json_client  # noqa: E402
from api.domain.polity.run_polity_simulation import ballots_today  # noqa: E402
from api.domain.polity.simple_rules import candidate_label  # noqa: E402

WORKERS = 8


def _scenarios(root: Path) -> list[dict[str, Any]]:
    """Every run's final state: its president, the constitution in force with no proposal pending, and the last
    legislative vote (read from the journal: checkpoints from before ADR-026 do not keep it)."""
    import run_polity_flagship as flagship

    found = []
    founding = flagship._flagship_config(
        engine="llm", years=8, population=100, seats=15, seed=1, output_dir=Path("/tmp/stakes-probe"),
        max_batch_replays=2, provider="vllm", workers=1, profile="exploration",
    )
    for checkpoint_path in sorted(root.rglob("checkpoint.json")):
        checkpoint = load_checkpoint(checkpoint_path)
        state, tick = checkpoint.state, checkpoint.tick
        ran = json.loads((checkpoint_path.parent / "config.json").read_text())
        rules = (ran["institutions"]["electoral_threshold"], ran["institutions"]["seat_allocation"],
                 ran["institutions"]["assembly_seats"], ran["sortition_chamber"]["seats"], len(state.citizens))
        if rules != (founding.institutions.electoral_threshold, founding.institutions.seat_allocation,
                     founding.institutions.assembly_seats, founding.sortition_chamber.seats, founding.run.population_size):
            print(f"skipped {checkpoint_path.parent}: founded on other rules than the exploration profile's {rules}")
            continue
        president = next((c for c in state.citizens if c.office == Office.PRESIDENT), None)
        if president is None or state.legislature is None:
            continue
        results = [json.loads(line) for line in (checkpoint_path.parent / "events.jsonl").open()
                   if '"legislative_result"' in line]
        state.legislature.votes = {int(p): v for p, v in results[-1]["payload"]["votes"].items()} if results else None
        constitution = dataclasses.replace(state.constitution, pending=None) if state.constitution else None
        config = in_force(founding, constitution)
        found.append(dict(run=f"{root.name}/{checkpoint_path.parent.name}", tick=tick, state=state, president=president,
                          constitution=constitution, config=config, today=(today := ballots_today(state, president, config)),
                          stakes=stakes_text(config, president, today, state.legislature,
                                             barred=is_term_limited(president, config.institutions.president_term_limit))))
    return found


def _turn(scenario: dict[str, Any], with_stakes: bool, sample: int) -> dict[str, Any] | None:
    config, state, president, tick = scenario["config"], scenario["state"], scenario["president"], scenario["tick"]
    text = constitution_text(config, scenario["constitution"], len(current_sortition_members(state.citizens)))
    stakes = scenario["stakes"] if with_stakes else None
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
        constitution=text, stakes=stakes,
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
    if amendment.article == "institutions.presidential_method" and scenario["today"]:
        wins = get_presidential_winner(scenario["today"], str(amendment.value)) == candidate_label(president)
    return {"run": scenario["run"], "article": amendment.article, "value": amendment.value, "wins": wins,
            "reason": amendment.reason, "band": _band(president.ambition_score)}


def _band(ambition: float) -> str:
    """ADR-028's bands: above 0.4 keeping office comes first, below 0.2 convictions do."""
    return "high" if ambition >= HIGH_AMBITION else "middle" if ambition >= LOW_AMBITION else "low"


def _at_risk(scenario: dict[str, Any]) -> bool:
    today, me = scenario["today"], candidate_label(scenario["president"])
    if not today or get_presidential_winner(today, scenario["config"].institutions.presidential_method) == me:
        return False
    return any(get_presidential_winner(today, str(m)) == me for m in ARTICLES["institutions.presidential_method"].choices)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roots", type=Path, nargs="+", help="directories of finished runs (their checkpoint.json and events.jsonl)")
    parser.add_argument("--samples", type=int, default=20, help="turns per president per arm")
    parser.add_argument("--at-risk", action="store_true",
                        help="ADR-027: only presidents today's ballots defeat under the method in force but elect under another")
    args = parser.parse_args(argv)
    scenarios = [s for root in args.roots for s in _scenarios(root)]
    me = {id(s): candidate_label(s["president"]) for s in scenarios}
    winning = sum(1 for s in scenarios if s["today"] and get_presidential_winner(s["today"], s["config"].institutions.presidential_method) == me[id(s)])
    at_risk = [s for s in scenarios if _at_risk(s)]
    print(f"today's ballots: {winning} presidents win under the method in force, {len(at_risk)} lose under it and win under "
          f"another, {len(scenarios) - winning - len(at_risk)} lose under every method or have none to count")
    if args.at_risk:
        scenarios = at_risk
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
        turns_by_band = collections.Counter(_band(s["president"].ambition_score) for s, _ in jobs)
        made_by_band = collections.Counter(p["band"] for p in made)
        print("  by ambition: " + ", ".join(f"{b} {made_by_band[b]} in {n} turns" for b, n in sorted(turns_by_band.items())))
        for (run, article, value), n in collections.Counter(
            (p["run"], p["article"].split(".")[-1], str(p["value"])) for p in made
        ).most_common():
            reason = next(p["reason"] for p in made
                          if p["run"] == run and p["article"].endswith(article) and str(p["value"]) == value)
            print(f"    {run}: {article} -> {value} x{n} -- {reason[:110]}")
        if methods:
            print(f"  voting-method proposals under which the president would have won: {sum(p['wins'] for p in methods)} of {len(methods)} "
                  f"({', '.join(sorted(str(p['value']) for p in methods))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
