"""EXP-031: the model arm, the rule-forum arm and the rule twin, side by side. CPU only.

Finished experiment script (see archive/README.md): not imported, not type-checked, not collected by CI. From fast_api_voter/:

    python scripts/archive/compare_rule_forum_arm.py <model-runs-dir> <rule-forum-dir> <twin-runs-dir>

The three directories are EXP-028's `stage2b`, the output of `run_rule_forum_founding.py`, and EXP-028's `stage2b-twin`. For each
arm it prints the archetypes, the divergence verdict, the band checks failed, the mean effective parties by seats, and the parties
founded and dissolved per run; then the mean pairwise distance within each arm and between arms, all three standardised together.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS.parent)]
import run_polity_catalogue as catalogue  # noqa: E402
from api.domain.polity.trajectory import (
    distance_matrix,
    diversity,
    divergence_by_year,
    divergence_verdict,
    pairwise_distances,
)  # noqa: E402


def load(base: Path, run_id: str, layout: str) -> dict:
    d = base / run_id / "run" / run_id if layout == "sweep" else base / run_id / run_id
    digest = json.loads((d / "digest.json").read_text())
    row = catalogue.read_trajectory(digest["trajectory"])
    row["yearly"] = digest["trajectory"]["yearly"]
    events = [
        json.loads(line)
        for line in (d / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    row["founded"] = sum(e["event_type"] == "party_founded" for e in events)
    row["dissolved"] = sum(e["event_type"] == "party_dissolved" for e in events)
    return row


def main(model: Path, rule: Path, twin: Path) -> None:
    arms = {
        "model": [
            load(model, f"stage2b-scenario-8y-p100-seed{s}", "sweep")
            for s in range(1, 11)
        ],
        "rule-forum": [load(rule, f"rule-forum-seed{s}", "flat") for s in range(1, 11)],
        "twin": [load(twin, f"sweep-8y-p100-seed{s}", "sweep") for s in range(1, 11)],
    }
    for arm, rows in arms.items():
        series = {f"{arm}{i}": r["yearly"] for i, r in enumerate(rows)}
        ensemble = diversity(
            {k: str(r["archetype"]) for k, r in zip(series, rows)},
            pairwise_distances(series),
        )
        verdict = divergence_verdict(
            divergence_by_year(series),
            ensemble,
            sum(not r["failed"] for r in rows) / len(rows),
        )
        print(
            f"\n{arm}: archetypes {dict(Counter(r['archetype'] for r in rows))}, entropy {ensemble['archetype_entropy_bits']:.2f} bits, inside the band {sum(not r['failed'] for r in rows)}/10, verdict {verdict}"
        )
        print(
            "  effective parties (mean over elections):",
            [round(r["enp"], 1) if r["enp"] else None for r in rows],
        )
        print(
            "  founded:",
            [r["founded"] for r in rows],
            "dissolved:",
            [r["dissolved"] for r in rows],
        )
        print(
            "  band checks failed:", dict(Counter(c for r in rows for c in r["failed"]))
        )
    series = {
        f"{arm}{i}": r["yearly"]
        for arm, rows in arms.items()
        for i, r in enumerate(rows)
    }
    pairs, matrix = distance_matrix(series)

    def mean(keep) -> float:
        idx = [i for i, (a, b) in enumerate(pairs) if keep(a, b)]
        return float(matrix[idx].mean())

    names = list(arms)
    print("\nmean pairwise distance, the 30 runs standardised together:")
    for a in names:
        print(
            f"  within {a:11s} {mean(lambda x, y, a=a: x.startswith(a) and y.startswith(a)):.2f}"
        )
    for i, a in enumerate(names):
        for b in names[i + 1 :]:

            def both(x: str, y: str, a: str = a, b: str = b) -> bool:
                return (x.startswith(a) and y.startswith(b)) or (
                    x.startswith(b) and y.startswith(a)
                )

            print(f"  between {a} / {b}: {mean(both):.2f}")


if __name__ == "__main__":
    main(*(Path(p).expanduser() for p in sys.argv[1:4]))
