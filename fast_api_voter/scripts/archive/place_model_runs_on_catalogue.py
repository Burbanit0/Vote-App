"""EXP-028 (Stage 2b): place ten model-led scenario runs on the rule-only catalogue's map.

Finished experiment script (see archive/README.md): not imported, not type-checked, not collected by CI.
Run from fast_api_voter/ at the commit of the runs (1456fef5), with the backend's venv:

    python scripts/run_polity_catalogue.py run --out <catalogue> --runs 1000 --seed 1 --years 8 --population 100 --workers 14
    python scripts/archive/place_model_runs_on_catalogue.py <model-runs-dir> <twin-runs-dir> <catalogue>

<model-runs-dir> holds stage2b-scenario-8y-p100-seed{1..10}/run/<id>/digest.json; <twin-runs-dir> holds the rule-only
twin's sweep-8y-p100-seed{1..10} (run_polity_seed_sweep.py --engine deterministic --profile scenario --seats 15).
Prints the archetypes, the band checks, the per-feature ranges, the model and twin runs outside the catalogue's p1-p99
envelope, each model run's nearest catalogue run in standardised feature space (with and without effective parties),
and the mean pairwise distance within each arm and between them with both arms standardised together.
"""

from __future__ import annotations

import json
import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS.parent)]
import run_polity_catalogue as catalogue  # noqa: E402
from api.domain.polity.trajectory import distance_matrix  # noqa: E402

KEYS = [
    "panel_stability",
    "holders",
    "alternations",
    "recalls",
    "turnout",
    "enp",
    "dispersion",
    "bimodality",
    "max_volatility",
]


def rows(base: Path, template: str) -> list[dict]:
    out = []
    for seed in range(1, 11):
        run_id = template.format(s=seed)
        digest = json.loads(
            (base / run_id / "run" / run_id / "digest.json").read_text()
        )
        row = catalogue.read_trajectory(digest["trajectory"])
        row["seed"] = seed
        row["yearly"] = digest["trajectory"]["yearly"]
        out.append(row)
    return out


def show(name: str, rs: list[dict]) -> None:
    print(f"\n{name} (n={len(rs)})")
    print(" archetypes", dict(Counter(r["archetype"] for r in rs)))
    print(" inside band", sum(not r["failed"] for r in rs), "/", len(rs))
    for k in KEYS:
        v = [r[k] for r in rs if r.get(k) is not None]
        if v:
            print(
                f"  {k:15s} min {min(v):.3f} med {statistics.median(v):.3f} max {max(v):.3f}"
            )


def quantile(v: list[float], p: float) -> float:
    v = sorted(v)
    return v[min(len(v) - 1, int(p * (len(v) - 1)))]


def main(model_dir: Path, twin_dir: Path, catalogue_dir: Path) -> None:
    model = rows(model_dir, "stage2b-scenario-8y-p100-seed{s}")
    twin = rows(twin_dir, "sweep-8y-p100-seed{s}")
    cat = [r for r in catalogue.load_rows(catalogue_dir) if "error" not in r]
    show("model", model)
    show("twin", twin)
    show("catalogue", cat)
    for arm, rs in (("model", model), ("twin", twin)):
        print(f"\n{arm} runs outside the catalogue's p1-p99 envelope:")
        for k in KEYS:
            cv = [r[k] for r in cat if r.get(k) is not None]
            lo, hi = quantile(cv, 0.01), quantile(cv, 0.99)
            out = [
                (r["seed"], round(r[k], 3))
                for r in rs
                if r.get(k) is not None and not lo <= r[k] <= hi
            ]
            print(f" {k:15s} [{lo:.3f},{hi:.3f}] outside: {out}")
    sd = {
        k: statistics.pstdev([r[k] for r in cat if r.get(k) is not None]) or 1
        for k in KEYS
    }

    def make_dist(keys: list[str]):
        def dist(a: dict, b: dict) -> float:
            return math.sqrt(
                sum(
                    ((a[k] - b[k]) / sd[k]) ** 2
                    for k in keys
                    if a.get(k) is not None and b.get(k) is not None
                )
            )

        return dist

    random.seed(0)
    sample = random.sample(cat, 100)
    for label, keys in (
        ("all nine features", KEYS),
        ("without effective parties", [k for k in KEYS if k != "enp"]),
    ):
        dist = make_dist(keys)
        print(
            f"\nnearest catalogue run, {label} (own archetype, nearest's archetype, distance in catalogue standard deviations)"
        )
        for r in model:
            n = min(cat, key=lambda b: dist(r, b))
            print(
                f" seed {r['seed']:2d} {r['archetype']:13s} -> {n['archetype']:13s} d={dist(r, n):.2f}"
            )
        nn = [min(dist(a, b) for b in cat if b is not a) for a in sample]
        print(
            f" catalogue to catalogue, 100 runs: median {statistics.median(nn):.2f}, p90 {quantile(nn, 0.9):.2f}"
        )
    print(
        "\narchetype shares in the catalogue:",
        {
            a: round(sum(r["archetype"] == a for r in cat) / len(cat), 3)
            for a in sorted({r["archetype"] for r in cat})
        },
    )
    # Both arms standardised together: the sweep summary standardises each arm on its own, so its distances do not compare across arms.
    series = {f"m{r['seed']}": r["yearly"] for r in model} | {
        f"t{r['seed']}": r["yearly"] for r in twin
    }
    pairs, matrix = distance_matrix(series)
    print("\nmean pairwise distance, both arms standardised together (20 runs):")
    for name, keep in (
        ("within model", lambda a, c: a[0] == c[0] == "m"),
        ("within twin", lambda a, c: a[0] == c[0] == "t"),
        ("between", lambda a, c: a[0] != c[0]),
    ):
        idx = [i for i, (a, c) in enumerate(pairs) if keep(a, c)]
        print(
            f" {name:13s} {matrix[idx].mean():.2f} over {len(idx)} pairs; by year {[round(float(x), 2) for x in matrix[idx].mean(axis=0)]}"
        )
    founders = []
    for arm in (model_dir,):
        for seed in range(1, 11):
            run_id = f"stage2b-scenario-8y-p100-seed{seed}"
            events = [
                json.loads(line)
                for line in (arm / run_id / "run" / run_id / "events.jsonl")
                .read_text()
                .splitlines()
                if line.strip()
            ]
            who = Counter(
                e["citizen_id"] for e in events if e["event_type"] == "party_founded"
            )
            born = {
                e["payload"]["party_id"]: e["tick"]
                for e in events
                if e["event_type"] == "party_founded"
            }
            dissolved = [
                e
                for e in events
                if e["event_type"] == "party_dissolved"
                and e["payload"]["party_id"] in born
            ]
            founders.append(
                (
                    sum(who.values()),
                    len(who),
                    max(who.values()),
                    len(dissolved),
                    sum(
                        e["tick"] - born[e["payload"]["party_id"]] < 4
                        for e in dissolved
                    ),
                )
            )
    print(
        "\nmodel arm per seed: (founded, distinct founders, most by one citizen, dissolved founded parties, of them inside the first year):"
    )
    print(founders)


if __name__ == "__main__":
    main(*(Path(p).expanduser() for p in sys.argv[1:4]))
