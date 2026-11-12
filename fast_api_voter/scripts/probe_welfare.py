"""ADR-034's table: for each (economic_voting, crisis) arm, ten seeds of the rule-only scenario twin, and what the
digest says about them: how office changed hands, the incumbent's mean approval, the archetypes and the
divergence test, the seeds inside the plausibility band.

Usage (from fast_api_voter/):
    python scripts/probe_welfare.py --output-dir /tmp/probe
    python scripts/probe_welfare.py --output-dir /tmp/probe --arm 2,12,-0.8 --arm 0

An arm is `voting` alone (no crisis) or `voting,tick,magnitude` (an economic shock at that tick). With no --arm,
ADR-034's seven. A reading, not a pre-registered experiment: one population size, one seed set.
"""
from __future__ import annotations

import argparse
import dataclasses
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import ScriptedEvent  # noqa: E402
from api.domain.polity.run_digest import build_digest, read_journal_tolerant  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.trajectory import divergence_by_year, divergence_verdict, diversity, pairwise_distances  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

Arm = tuple[float, tuple[int, float] | None]
ADR_ARMS: tuple[Arm, ...] = (
    (0.0, None), (1.0, None), (2.0, None), (0.0, (12, -0.8)), (1.0, (12, -0.8)), (2.0, (12, -0.8)), (2.0, (12, 0.8)),
)
SEEDS = range(1, 11)


def parse_arm(text: str) -> Arm:
    parts = [float(x) for x in text.split(",")]
    return (parts[0], None) if len(parts) == 1 else (parts[0], (int(parts[1]), parts[2]))


def run_arm(voting: float, crisis: tuple[int, float] | None, output_dir: Path) -> dict[str, Any]:
    label = f"{voting}-{crisis}"
    series, labels, in_band = {}, {}, 0
    approvals: list[float] = []
    alternations: list[int] = []
    reelections: list[int] = []
    recalls: list[int] = []
    for seed in SEEDS:
        config = _flagship_config(
            engine="deterministic", years=8, population=100, seats=15, seed=seed, output_dir=output_dir / label / str(seed),
            max_batch_replays=0, provider=None, workers=1, profile="scenario",
        )
        scripted = () if crisis is None else (ScriptedEvent(crisis[0], "economic_shock", crisis[1]),)
        config = dataclasses.replace(
            config, events=dataclasses.replace(config.events, scripted=scripted), vote=dataclasses.replace(config.vote, economic_voting=voting),
        )
        journal = run_simulation(config, run_id="probe")
        trajectory = build_digest(journal, config, run_id="probe", outcome="completed", resume=False)["trajectory"]
        events, _ = read_journal_tolerant(journal)
        approvals.append(statistics.mean(e["payload"]["approval"] for e in events if e["event_type"] == "legitimacy_updated" and "approval" in e["payload"]))
        series[f"seed {seed}"], labels[f"seed {seed}"] = trajectory["yearly"], trajectory["archetype"]
        in_band += not trajectory["plausibility_failed"]
        office = trajectory["office"]
        alternations.append(office["alternations"])
        reelections.append(office["reelections"])
        recalls.append(office["recalls"])
    ensemble, by_year = diversity(labels, pairwise_distances(series)), divergence_by_year(series)
    return {
        "approval": statistics.mean(approvals), "alternations": statistics.mean(alternations), "reelections": statistics.mean(reelections),
        "recalls": statistics.mean(recalls), "archetypes": ensemble["archetypes"], "entropy": ensemble["archetype_entropy_bits"],
        "distance": (by_year[0], by_year[-1]), "in_band": in_band, "verdict": divergence_verdict(by_year, ensemble, in_band / len(SEEDS)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--arm", action="append", default=[], help="voting | voting,tick,magnitude (repeatable)")
    args = parser.parse_args(argv)
    for voting, crisis in [parse_arm(a) for a in args.arm] or list(ADR_ARMS):
        r = run_arm(voting, crisis, args.output_dir)
        print(f"voting {voting} crisis {crisis}: approval {r['approval']:.3f} alternations {r['alternations']:.1f} reelections {r['reelections']:.1f} "
              f"recalls {r['recalls']:.1f} {r['archetypes']} {r['entropy']:.2f} bits distance {r['distance'][0]:.2f}->{r['distance'][1]:.2f} "
              f"in band {r['in_band']}/10 {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
