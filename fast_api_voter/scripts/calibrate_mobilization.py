"""D9's recalibration: the deterministic twin's mobilization against the LLM path's.

Pre-registered in plan-polity-build-order.md ("D9's recalibration, pre-registered before
running"), signed off by the owner and committed before this script ran. It is run exactly as
written there:

- **The knob.** `mobilization_threshold_scale`: a consulted citizen mobilizes only when their gap
  reaches `scale x blank_threshold x tolerance_scale`; past the ordinary threshold but short of
  that, they do nothing. Petition branches are untouched.
- **The target.** Pooled over the twin's seeds, MOBILIZE at most 2.0% of consulted acts, and
  SIGN_PETITION within 12-20% as a guard.
- **The grid.** Twelve scales from 1.00 to 3.00, fixed before running.
- **Selection.** The smallest scale inside both. None inside means none qualifies.
- **The gate**, reported for the selected scale and never used to select it: at most 3 recalls
  per seed on average, and at least 10 of 20 full terms.

The setting does not exist in the product yet, so the rule is applied here by wrapping the
engine's own `deterministic_pressure_action`, changing only a MOBILIZE outcome below the scaled
threshold. When a scale is adopted, the setting lands in `simple_rules` and this grid is re-run
through it: the numbers must come out identical.

Usage (from fast_api_voter/):
    python scripts/calibrate_mobilization.py   # writes calibrate_mobilization_results.{md,json}
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import api.domain.polity.run_polity_simulation as engine  # noqa: E402
from api.domain.polity.codebook import PressureAct  # noqa: E402
from api.domain.polity.simple_rules import deterministic_pressure_action  # noqa: E402
from probe_twin_presidency import FULL_TERM_TICKS, YEARS, act_counts, spans  # noqa: E402
from twin_runs import SEEDS, run_twin, twin_config  # noqa: E402

GRID = (1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40, 1.50, 1.75, 2.00, 2.50, 3.00)
MOBILIZE_MAX = 0.020
SIGN_PETITION_BAND = (0.12, 0.20)
GATE_RECALLS_PER_SEED = 3.0
GATE_FULL_TERMS = 10
RESULTS = Path(__file__).resolve().parent / "calibrate_mobilization_results"


def scaled_rule(scale: float) -> Callable[..., PressureAct]:
    """The engine's rule, with a MOBILIZE below `scale` times the threshold turned into NOTHING."""
    def rule(citizen: Any, gap: float, menu: Any, *, can_sign: bool = False, can_launch: bool = False,
             tolerance_scale: float = 1.0) -> PressureAct:
        act = deterministic_pressure_action(citizen, gap, menu, can_sign=can_sign, can_launch=can_launch,
                                            tolerance_scale=tolerance_scale)
        if act == PressureAct.MOBILIZE and gap < citizen.blank_threshold * tolerance_scale * scale:
            return PressureAct.NOTHING
        return act
    return rule


@contextmanager
def mobilization_scale(scale: float) -> Iterator[None]:
    real = engine.deterministic_pressure_action
    engine.deterministic_pressure_action = scaled_rule(scale)  # type: ignore[assignment]
    try:
        yield
    finally:
        engine.deterministic_pressure_action = real  # type: ignore[assignment]


def measure(scale: float) -> dict[str, Any]:
    acts: Counter[str] = Counter()
    recalls = 0
    full_terms = 0
    lengths: list[int] = []
    with mobilization_scale(scale):
        for seed in SEEDS:
            events = run_twin(twin_config(seed=seed, years=YEARS))
            acts += act_counts(events)
            finished = [(length, how) for length, how in spans(events) if how != "run_end"]
            recalls += sum(1 for _, how in finished if how == "recalled")
            full_terms += sum(1 for length, _ in finished if length >= FULL_TERM_TICKS)
            lengths += [length for length, _ in finished]
    consulted = sum(acts.values())
    mobilize = acts["MOBILIZE"] / consulted if consulted else 0.0
    sign = acts["SIGN_PETITION"] / consulted if consulted else 0.0
    return {
        "scale": scale,
        "consulted_acts": consulted,
        "mobilize_share": mobilize,
        "sign_petition_share": sign,
        "in_band": mobilize <= MOBILIZE_MAX and SIGN_PETITION_BAND[0] <= sign <= SIGN_PETITION_BAND[1],
        "recalls_per_seed": recalls / len(SEEDS),
        "full_terms": full_terms,
        "median_presidency_ticks": statistics.median(lengths) if lengths else None,
    }


def main() -> int:
    rows = []
    for scale in GRID:
        rows.append(measure(scale))
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
    selected = next((row for row in rows if row["in_band"]), None)
    gate = None
    if selected is not None:
        gate = {
            "recalls_per_seed_ok": selected["recalls_per_seed"] <= GATE_RECALLS_PER_SEED,
            "full_terms_ok": selected["full_terms"] >= GATE_FULL_TERMS,
        }
        gate["holds"] = gate["recalls_per_seed_ok"] and gate["full_terms_ok"]

    (RESULTS.with_suffix(".json")).write_text(json.dumps(
        {"grid": rows, "selected": selected, "gate": gate}, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# D9's recalibration: the twin's mobilization against the LLM path's",
        "",
        "Generated by `scripts/calibrate_mobilization.py`, run as pre-registered in "
        "`plan-polity-build-order.md` (\"D9's recalibration, pre-registered before running\").",
        "",
        f"Target: MOBILIZE ≤ {MOBILIZE_MAX:.1%} of consulted acts, SIGN_PETITION within "
        f"{SIGN_PETITION_BAND[0]:.0%}–{SIGN_PETITION_BAND[1]:.0%}. The twin: population 100, seeds "
        f"{SEEDS[0]}–{SEEDS[-1]}, {YEARS} years.",
        "",
        "| scale | consulted acts | MOBILIZE | SIGN_PETITION | in band | recalls per seed | full terms (of 20) | median presidency |",
        "|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for row in rows:
        median = f"{row['median_presidency_ticks']:g}" if row["median_presidency_ticks"] is not None else "—"
        lines.append(
            f"| {row['scale']:.2f} | {row['consulted_acts']:,} | {row['mobilize_share']:.2%} "
            f"| {row['sign_petition_share']:.1%} | {'**yes**' if row['in_band'] else 'no'} "
            f"| {row['recalls_per_seed']:.1f} | {row['full_terms']} | {median} |")
    lines += ["", "## Selection"]
    if selected is None:
        lines += ["", "**None qualifies.** No scale on the pre-registered grid brings MOBILIZE inside its band "
                      "with SIGN_PETITION inside its guard. D9 stays open."]
    else:
        lines += ["", f"**Selected: scale {selected['scale']:.2f}**, the smallest inside both bands.", "",
                  "## The gate", "",
                  f"- Recalls per seed: {selected['recalls_per_seed']:.1f}, needs ≤ {GATE_RECALLS_PER_SEED:g} — "
                  f"{'**holds**' if gate and gate['recalls_per_seed_ok'] else '**fails**'}",
                  f"- Full terms: {selected['full_terms']} of 20, needs ≥ {GATE_FULL_TERMS} — "
                  f"{'**holds**' if gate and gate['full_terms_ok'] else '**fails**'}",
                  "",
                  ("**The gate holds.** Per the pre-registration, the scale is adopted as the deterministic "
                   "default and S4.1, S4.3 and S4.2 are re-run unchanged." if gate and gate["holds"] else
                   "**The gate fails.** Per the pre-registration, the twin still cannot stand in for the LLM "
                   "path's presidency, and the Stage 4 calibrations are not re-run.")]
    RESULTS.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {RESULTS.name}.{{md,json}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
