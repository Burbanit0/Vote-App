"""S4.3's calibration: opinion dynamics, then emotions, against ADR-012's pre-registered facts.

The twin is run_polity_flagship.py's full-mechanism config at population 100 (social graph
on), deterministic, seeds 1-10, 8 years, every other Stage 4 mechanism at its shipped setting
(off). ADR-012 pre-registered the grids, the facts and the selection; three readings it left
open were fixed here before the grid ran (2026-09-13):

- **D2** averages the year-8 over year-0 spread ratio over runs and both factors (as D1
  averages its correlations), and reports the lowest single ratio beside it.
- **Year 0** of a panel is the population's initial factors (`LatentStructure.anchors`): the
  year-0 snapshot is taken before any update, so it carries no factors. The static arm's
  panel is its anchors at every year.
- **Emotions** are calibrated with the adopted dynamics setting, or on the static population
  when none qualifies. If the smallest qualifying weight set is all zeros, the facts hold
  without emotions acting on anything, and emotions stay off. Equal total weights go to the
  earlier setting in grid order.

Adopting a setting means `polity_config.yaml` carries its values with `enabled: false` (the
shipped base has no social graph, which influence needs) and run_polity_flagship.py's
full-mechanism config, where it was measured, turns the mechanism on.

Usage (from fast_api_voter/):
    python scripts/calibrate_dynamic_citizens.py   # writes calibrate_dynamic_citizens_results.{md,json}
"""
from __future__ import annotations

import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.citizen import latent_structure  # noqa: E402
from api.domain.polity.config import PolityConfig  # noqa: E402
from api.domain.polity.social_graph import generate_social_graph  # noqa: E402
from api.domain.polity.twin_calibration import (  # noqa: E402
    Arm,
    Term,
    TickMood,
    closest_to,
    discontent_mobilizes,
    dispersion_kept,
    grid,
    hard_times_draw_in,
    homophily,
    honeymoon_decline,
    more_presidents,
    neighbour_distance_ratio,
    panel_correlation,
    panel_stability,
    select,
)
from twin_runs import SEEDS, run_twin_with_snapshots, twin_config  # noqa: E402

DYNAMICS_AXES = {"susceptibility": (0.90, 0.95, 0.98), "influence_step": (0.1, 0.2, 0.4),
                 "confidence_bound": (0.5, 1.0, 2.0), "drift_std": (0.02, 0.05, 0.10)}
EMOTION_AXES = {"awakening_anger": (0.0, 0.25, 0.5), "awakening_anxiety": (0.0, 0.25, 0.5),
                "awakening_enthusiasm": (0.0, 0.25, 0.5), "mobilization_anger": (0.0, 0.25, 0.5)}
YEARS = 8
LAST_YEAR = YEARS
RESULTS = Path(__file__).resolve().parent / "calibrate_dynamic_citizens_results"


@dataclasses.dataclass
class Runs:
    panels: list[dict[int, np.ndarray]] = dataclasses.field(default_factory=list)
    ratios: list[tuple[float | None, float | None]] = dataclasses.field(default_factory=list)
    winners: list[list[int]] = dataclasses.field(default_factory=list)
    moods: list[TickMood] = dataclasses.field(default_factory=list)
    terms: list[Term] = dataclasses.field(default_factory=list)


def _config(seed: int, dynamics: dict[str, float] | None, emotions: dict[str, float] | None) -> PolityConfig:
    config = twin_config(seed, YEARS)
    if dynamics is not None:
        config = dataclasses.replace(config, dynamics=dataclasses.replace(config.dynamics, enabled=True, **dynamics))
    if emotions is not None:
        config = dataclasses.replace(config, emotions=dataclasses.replace(config.emotions, enabled=True, **emotions))
    return config


def _moods(seed: int, events: list[dict[str, Any]]) -> list[TickMood]:
    actions = Counter(e["tick"] for e in events if e["event_type"] == "pressure_action")
    mobilized = Counter(e["tick"] for e in events if e["event_type"] == "pressure_action" and e["payload"]["act"] == 3)
    return [TickMood(seed=seed, tick=e["tick"], anger=e["payload"]["anger"], anxiety=e["payload"]["anxiety"],
                     enthusiasm=e["payload"]["enthusiasm"], pressure_actions=actions[e["tick"]], mobilizations=mobilized[e["tick"]])
            for e in events if e["event_type"] == "emotions_updated"]


def _full_terms(seed: int, events: list[dict[str, Any]], term_ticks: int) -> list[Term]:
    recalls = [e["tick"] for e in events if e["event_type"] == "recalled"]
    return [Term(seed=seed, start=e["tick"]) for e in events if e["event_type"] == "elected"
            and not any(e["tick"] <= r < e["tick"] + term_ticks for r in recalls)]


def measure(dynamics: dict[str, float] | None, emotions: dict[str, float] | None) -> Runs:
    runs = Runs()
    for seed in SEEDS:
        config = _config(seed, dynamics, emotions)
        events, snapshots = run_twin_with_snapshots(config)
        n = config.run.population_size
        anchors = latent_structure(config.citizens, n, seed).anchors
        panel = {0: anchors}
        for year in range(1, LAST_YEAR + 1):
            rows = sorted((r for r in snapshots if r["year"] == year), key=lambda r: r["citizen_id"])
            panel[year] = np.array([r["latent_factors"] for r in rows]) if rows and "latent_factors" in rows[0] else anchors
        graph = generate_social_graph(config.social_graph, n, seed)
        pairs = np.array(sorted((a, b) for a, ns in graph.neighbors.items() for b in ns if a < b), dtype=np.int64).reshape(-1, 2)
        runs.panels.append(panel)
        runs.ratios.append((neighbour_distance_ratio(panel[0], pairs), neighbour_distance_ratio(panel[LAST_YEAR], pairs)))
        runs.winners.append([e["citizen_id"] for e in events if e["event_type"] == "elected"])
        runs.moods += _moods(seed, events)
        term_ticks = config.institutions.president_term_years * config.run.ticks_per_year
        runs.terms += _full_terms(seed, events, term_ticks)
    return runs


def dynamics_arm(setting: dict[str, Any], runs: Runs, static: Runs) -> Arm:
    return Arm(setting=setting,
               facts=(panel_stability(runs.panels), dispersion_kept(runs.panels), homophily(runs.ratios),
                      more_presidents(runs.winners, static.winners)),
               measures={"panel_correlation": _mean_correlation(runs)})


def _mean_correlation(runs: Runs) -> float | None:
    values = [v for v in (panel_correlation(panel, 4) for panel in runs.panels) if v is not None]
    return sum(values) / len(values) if values else None


def emotions_arm(setting: dict[str, Any], runs: Runs) -> Arm:
    config = twin_config(SEEDS[0], YEARS)
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year
    return Arm(setting=setting,
               facts=(discontent_mobilizes(runs.moods), hard_times_draw_in(runs.moods),
                      honeymoon_decline(runs.moods, runs.terms, term_ticks, config.run.ticks_per_year)),
               measures={"total_weight": float(sum(setting.values()))})


def _setting(setting: dict[str, Any] | None) -> str:
    return "static population" if setting is None else ", ".join(f"{k} {v}" for k, v in setting.items())


def _table(arms: list[Arm]) -> list[str]:
    names = [fact.name for fact in arms[0].facts]
    lines = ["| setting | " + " | ".join(names) + " | all |", "|---|" + "---|" * (len(names) + 1)]
    for arm in arms:
        cells = [f"{'✓' if f.holds else '✗'} {f.reading}" for f in arm.facts]
        lines.append(f"| {_setting(arm.setting)} | " + " | ".join(cells) + f" | {'✓' if arm.qualifies else '✗'} |")
    return lines


def markdown(static: Arm, dynamics_arms: list[Arm], chosen_dynamics: Arm | None,
             emotion_arms: list[Arm], chosen_emotions: Arm | None, emotions_adopted: bool) -> str:
    return "\n".join([
        "# S4.3 calibration: dynamic citizens (ADR-012)", "",
        "Generated by `scripts/calibrate_dynamic_citizens.py`. Twin: full-mechanism config, population 100, "
        f"deterministic, seeds {SEEDS[0]}-{SEEDS[-1]}, {YEARS} years. Grids, facts and selection pre-registered in "
        "ADR-012; readings it left open fixed before running (see the script's docstring).", "",
        "## Verdict", "",
        f"- **Dynamics:** {'adopted: ' + _setting(chosen_dynamics.setting) if chosen_dynamics else 'nothing qualifies; the population stays static'} "
        f"({sum(a.qualifies for a in dynamics_arms)} of {len(dynamics_arms)} settings meet D1-D4).",
        f"- **Emotions** (calibrated on {_setting(chosen_dynamics.setting if chosen_dynamics else None)}): "
        + (f"adopted: {_setting(chosen_emotions.setting)}" if emotions_adopted and chosen_emotions
           else "the smallest qualifying weights are all zero, so emotions stay off" if chosen_emotions
           else "nothing qualifies; emotions stay off")
        + f" ({sum(a.qualifies for a in emotion_arms)} of {len(emotion_arms)} settings meet E1-E3).", "",
        "## Static arm", "", *[f"- {f.name}: {f.reading}" for f in static.facts], "",
        "## Dynamics settings", "", *_table(dynamics_arms), "",
        "## Emotion settings", "", *_table(emotion_arms), "",
    ])


def main() -> int:
    static_runs = measure(None, None)
    static = dynamics_arm({}, static_runs, static_runs)
    dynamics_arms = []
    for setting in grid(DYNAMICS_AXES):
        dynamics_arms.append(dynamics_arm(setting, measure(setting, None), static_runs))
        print("dynamics", _setting(setting), "qualifies" if dynamics_arms[-1].qualifies else "", flush=True)
    chosen_dynamics = select(dynamics_arms, closest_to(0.80, "panel_correlation"))
    base = chosen_dynamics.setting if chosen_dynamics else None
    emotion_arms = []
    for setting in grid(EMOTION_AXES):
        emotion_arms.append(emotions_arm(setting, measure(base, setting)))
        print("emotions", _setting(setting), "qualifies" if emotion_arms[-1].qualifies else "", flush=True)
    chosen_emotions = select(emotion_arms, lambda arm: arm.measures["total_weight"])
    emotions_adopted = chosen_emotions is not None and any(chosen_emotions.setting.values())
    RESULTS.with_suffix(".md").write_text(
        markdown(static, dynamics_arms, chosen_dynamics, emotion_arms, chosen_emotions, emotions_adopted), encoding="utf-8")
    RESULTS.with_suffix(".json").write_text(json.dumps({
        "static": dataclasses.asdict(static), "dynamics": [dataclasses.asdict(a) for a in dynamics_arms],
        "chosen_dynamics": dataclasses.asdict(chosen_dynamics) if chosen_dynamics else None,
        "emotions": [dataclasses.asdict(a) for a in emotion_arms],
        "chosen_emotions": dataclasses.asdict(chosen_emotions) if chosen_emotions else None,
        "emotions_adopted": emotions_adopted,
    }, indent=2), encoding="utf-8")
    print("dynamics:", _setting(base) if chosen_dynamics else None, "| emotions:",
          _setting(chosen_emotions.setting) if emotions_adopted and chosen_emotions else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
