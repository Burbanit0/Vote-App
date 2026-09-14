"""S4.2's calibration: ordinary legislation against ADR-009's pre-registered facts.

The twin is run_polity_flagship.py's full-mechanism config at population 100 (sortition
chamber on), deterministic, seeds 1-10, 16 years, legislation on, every other Stage 4
mechanism at its shipped setting (off). ADR-009 pre-registered the grid (bill interval
{1, 2, 4} x step {0.05, 0.1, 0.2} x policy_retrospection {0, 2, 5, 10}), the facts and the
selection. Readings it left open were fixed here before the grid ran (2026-09-13):

- **L1** averages over ticks from the first legislative election on: before an assembly
  exists policy sits at the median by construction and no bill can pass.
- **L2**'s "per presidential term" pools enacted bills over `elected` events across runs.
- **L3** classifies a bill by its agenda setter (the government sets it only under
  cohabitation) and, for a president's bill, by the last coalition event: formed is unified
  government, failed is no government (neither regime). Unmeasured does not hold.
- **L4**'s vote share is over every ballot, blank ballots included. A spell starts at a
  legislative election that formed a coalition and ends at the next one; an election where no
  coalition formed starts none.
- **Selection.** A setting (interval, step) qualifies when L1-L3 hold at retrospection 0 and some
  weight meets L4; its weight is the smallest that does. Among qualifying settings, the longest
  interval, then the smallest step.

Adopting a setting means `polity_config.yaml` carries its values with `legislation.enabled:
false` and the adopted `vote.policy_retrospection`, and run_polity_flagship.py's full-mechanism
config turns legislation on.

Usage (from fast_api_voter/):
    python scripts/calibrate_legislation.py   # writes calibrate_legislation_results.{md,json}
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.accountability import current_office_holders  # noqa: E402
from api.domain.polity.citizen import Office  # noqa: E402
from api.domain.polity.legislation import population_median, rms_distance  # noqa: E402
from api.domain.polity.twin_calibration import (  # noqa: E402
    Arm,
    Draft,
    GovernmentSpell,
    PolicyTick,
    checks_moderate,
    gridlock_under_cohabitation,
    legislation_alive,
    legislation_choice,
    lowest_qualifying_weight,
    mean_share_change,
    select,
)
from twin_runs import SEEDS, observing, run_twin, twin_config  # noqa: E402

INTERVALS = (1, 2, 4)
STEPS = (0.05, 0.1, 0.2)
WEIGHTS = (0.0, 2.0, 5.0, 10.0)
YEARS = 16
RESULTS = Path(__file__).resolve().parent / "calibrate_legislation_results"


@dataclasses.dataclass
class Runs:
    ticks: list[PolicyTick] = dataclasses.field(default_factory=list)
    drafts: list[Draft] = dataclasses.field(default_factory=list)
    enacted: list[int] = dataclasses.field(default_factory=list)
    terms: list[int] = dataclasses.field(default_factory=list)
    spells: list[GovernmentSpell] = dataclasses.field(default_factory=list)


def _drafts(seed: int, events: list[dict[str, Any]]) -> list[Draft]:
    enacted = {e["payload"]["bill_id"] for e in events if e["event_type"] == "bill_enacted"}
    drafts, coalition_formed = [], None
    for e in events:
        if e["event_type"] in ("coalition_formed", "coalition_failed"):
            coalition_formed = e["event_type"] == "coalition_formed"
        elif e["event_type"] == "bill_proposed":
            if e["payload"]["agenda_setter"] == "government":
                regime = "cohabitation"
            else:
                regime = "unified" if coalition_formed else "no_government"
            drafts.append(Draft(seed=seed, regime=regime, enacted=e["payload"]["bill_id"] in enacted))
    return drafts


def _spells(seed: int, events: list[dict[str, Any]]) -> list[GovernmentSpell]:
    results = [e for e in events if e["event_type"] == "legislative_result"]
    coalitions = {e["tick"]: e["payload"]["coalition"] for e in events if e["event_type"] in ("coalition_formed", "coalition_failed")}

    def share(result: dict[str, Any], parties: list[int]) -> float:
        votes = result["payload"]["votes"]
        ballots = sum(votes.values()) + result["payload"]["blank_count"]
        return sum(votes.get(str(p), 0.0) for p in parties) / ballots if ballots else 0.0

    return [GovernmentSpell(seed=seed, share_at_formation=share(now, coalitions[now["tick"]]), share_next=share(later, coalitions[now["tick"]]))
            for now, later in zip(results, results[1:]) if coalitions.get(now["tick"])]


def measure(interval: int, step: float, weight: float) -> Runs:
    runs = Runs()
    for seed in SEEDS:
        config = twin_config(seed, YEARS)
        config = dataclasses.replace(
            config, legislation=dataclasses.replace(config.legislation, enabled=True, bill_interval_ticks=interval, max_bill_step=step),
            vote=dataclasses.replace(config.vote, policy_retrospection=weight),
        )

        def observe(context: Any, state: Any, seed: int = seed) -> None:
            legislature = state.legislature
            president = next((h for h in current_office_holders(state.citizens, Office.PRESIDENT) if h.revealed_position is not None), None)
            if legislature is None or legislature.seats is None or president is None:
                return
            median = population_median(state.citizens)
            runs.ticks.append(PolicyTick(seed=seed, tick=context.tick, policy_distance=rms_distance(legislature.policy, median),
                                         president_distance=rms_distance(president.revealed_position, median)))

        with observing(observe):
            events = run_twin(config)
        runs.drafts += _drafts(seed, events)
        runs.enacted.append(sum(e["event_type"] == "bill_enacted" for e in events))
        runs.terms.append(sum(e["event_type"] == "elected" for e in events))
        runs.spells += _spells(seed, events)
    return runs


def _setting(setting: dict[str, Any]) -> str:
    return ", ".join(f"{k} {v}" for k, v in setting.items())


def main() -> int:
    arms = []
    for interval in INTERVALS:
        for step in STEPS:
            by_weight = [(weight, measure(interval, step, weight)) for weight in WEIGHTS]
            zero = by_weight[0][1]
            weight, l4 = lowest_qualifying_weight([(w, r.spells) for w, r in by_weight if w > 0], zero.spells)
            arm = Arm(
                setting={"bill_interval_ticks": interval, "max_bill_step": step, "policy_retrospection": weight},
                facts=(checks_moderate(zero.ticks), legislation_alive(zero.enacted, zero.terms), gridlock_under_cohabitation(zero.drafts), l4),
                measures={f"share_change_at_{w:g}": mean_share_change(r.spells) for w, r in by_weight},
            )
            arms.append(arm)
            print(_setting(arm.setting), "qualifies" if arm.qualifies else "", flush=True)
    chosen = select(arms, legislation_choice)
    names = [f.name for f in arms[0].facts]
    lines = [
        "# S4.2 calibration: ordinary legislation (ADR-009)", "",
        "Generated by `scripts/calibrate_legislation.py`. Twin: full-mechanism config, population 100, deterministic, "
        f"seeds {SEEDS[0]}-{SEEDS[-1]}, {YEARS} years, legislation on. Grid, facts and selection pre-registered in ADR-009; "
        "readings it left open fixed before running (see the script's docstring). L1-L3 are read at retrospection 0; "
        "L4 names the smallest weight meeting it.", "",
        "## Verdict", "",
        (f"**Adopted:** {_setting(chosen.setting)}." if chosen else "**Nothing qualifies:** legislation stays off."), "",
        f"{sum(a.qualifies for a in arms)} of {len(arms)} settings meet L1-L4.", "",
        "## Every setting", "",
        "| interval, step | " + " | ".join(names) + " | L4 weight | all |", "|---|" + "---|" * (len(names) + 2),
    ]
    for arm in arms:
        cells = [f"{'✓' if f.holds else '✗'} {f.reading}" for f in arm.facts]
        lines.append(f"| {arm.setting['bill_interval_ticks']}, {arm.setting['max_bill_step']} | " + " | ".join(cells)
                     + f" | {arm.setting['policy_retrospection']} | {'✓' if arm.qualifies else '✗'} |")
    RESULTS.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    RESULTS.with_suffix(".json").write_text(json.dumps(
        {"arms": [dataclasses.asdict(a) for a in arms], "chosen": dataclasses.asdict(chosen) if chosen else None}, indent=2), encoding="utf-8")
    print("chosen:", _setting(chosen.setting) if chosen else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
