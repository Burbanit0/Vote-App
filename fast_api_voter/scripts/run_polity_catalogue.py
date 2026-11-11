"""The catalogue of scenarios (plan-scenarios-v1, step 6): a Latin hypercube over the institutional and environmental
settings of `api.domain.polity.catalogue.DIMENSIONS`, each point run once on the rule-only scenario twin, each run read
into a row (archetype, plausibility checks, a few numbers), and PRIM boxes per archetype over the rows.

Usage (from fast_api_voter/):
    python scripts/run_polity_catalogue.py run    --out /tmp/catalogue --runs 1000
    python scripts/run_polity_catalogue.py report --out /tmp/catalogue

`run` appends to <out>/rows.jsonl and skips the points already there, so an interrupted sweep resumes (same --runs and
--seed give the same points). Each run is `--years` years of `--population` citizens with a seed of its own; its run
directory is removed once its row is written. `report` writes <out>/report.md and prints it.

A reading, not a pre-registered experiment: one population size, one run per point, the seed a nuisance variable that
PRIM is not told about. The twin has no model, so settings that act through the agents (the amendment threshold) are inert
by construction and stay in as the negative control.
"""
from __future__ import annotations

import argparse
import collections
import json
import concurrent.futures
import multiprocessing
import shutil
import statistics
import sys
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.catalogue import DIMENSIONS, Box, apply_point, prim, relabel, sample  # noqa: E402
from api.domain.polity.checkpoint import config_hash  # noqa: E402
from api.domain.polity.config import validate_config  # noqa: E402
from api.domain.polity.run_digest import build_digest  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.trajectory import ARCHETYPE_VERSION, REALIGNMENT_SPREADS, largest_relative_shift  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

NON_TRIVIAL = 0.05
"""An archetype counts when at least this share of the runs read as it."""
MIN_CLASS_ROWS = 20
"""An archetype with fewer runs than this is counted but its box is not read: a box of a handful of points is noise."""
MIN_BAND_ROWS = 60
"""Below this many runs inside the plausibility band the band-only boxes are not worth reading."""


def run_point(job: tuple[int, dict[str, Any], int, int, int, str]) -> dict[str, Any]:
    """One point, one run, one row. A run that raises is a row with its error, not a crash of the sweep."""
    index, point, seed, years, population, out = job
    run_dir = Path(out) / "runs" / str(index)
    row: dict[str, Any] = {"index": index, "seed": seed, "point": point}
    try:
        config = _flagship_config(
            engine="deterministic", years=years, population=population, seats=max(5, population // 7), seed=seed,
            output_dir=run_dir, max_batch_replays=0, provider=None, workers=1, profile="scenario",
        )
        config = apply_point(config, point)
        validate_config(config)
        journal = run_simulation(config, run_id="catalogue")
        trajectory = build_digest(journal, config, run_id="catalogue", outcome="completed", resume=False)["trajectory"]
        row.update(read_trajectory(trajectory))
    except Exception as error:  # noqa: BLE001 -- recorded, so one bad point does not lose the sweep
        row["error"] = f"{type(error).__name__}: {error}"
        row["trace"] = traceback.format_exc(limit=-3)
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
    return row


def read_trajectory(trajectory: dict[str, Any]) -> dict[str, Any]:
    """The row a run leaves: its archetype, the plausibility checks it failed, and a few numbers."""
    office, legislative = trajectory["office"], trajectory["legislative"]
    enp = [x["enp_seats"] for x in legislative if x["enp_seats"] is not None]
    polarization = trajectory["polarization"]
    last = polarization[-1] if polarization else {"dispersion": None, "bimodality": None}
    return {
        "archetype": trajectory["archetype"],
        "failed": list(trajectory["plausibility_failed"]),
        "panel_stability": trajectory["panel_stability"],
        "holders": office["distinct_holders"],
        "alternations": office["alternations"],
        "recalls": office["recalls"],
        "turnout": statistics.mean(e["turnout"] for e in trajectory["elections"]) if trajectory["elections"] else None,
        "enp": statistics.mean(enp) if enp else None,
        "dispersion": last["dispersion"],
        "bimodality": last["bimodality"],
        # what the rules past the first five read, so a run can be relabelled at another realignment threshold (the
        # catalogue's runs never meet the earlier rules): the largest shift against the first census's own spread
        "max_shift": max((row["mean_shift"] for row in polarization), default=0.0),
        "max_rel_shift": largest_relative_shift(polarization),
        "max_volatility": max((x["volatility"] for x in legislative if x["volatility"] is not None), default=0.0),
    }


def profile_hash(years: int, population: int) -> str:
    """The scenario profile's rules as the sweep's points start from (seed and run directory fixed, so only the profile
    and the engine's settings show): a change of the profile, like ADR-038's weight, is a different sweep."""
    base = _flagship_config(
        engine="deterministic", years=years, population=population, seats=max(5, population // 7), seed=0,
        output_dir=Path("catalogue"), max_batch_replays=0, provider=None, workers=1, profile="scenario",
    )
    return config_hash(base)


def load_rows(out: Path) -> list[dict[str, Any]]:
    """The rows written so far, the latest row of each point (a point that errored and was run again has its new row)."""
    path = out / "rows.jsonl"
    latest = {row["index"]: row for row in map(json.loads, path.read_text().splitlines())} if path.exists() else {}
    return [latest[i] for i in sorted(latest)]


def run(args: argparse.Namespace) -> int:
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    settings = {
        "runs": args.runs, "seed": args.seed, "years": args.years, "population": args.population,
        "archetype_version": ARCHETYPE_VERSION, "profile": profile_hash(args.years, args.population),
        "dimensions": [d.name for d in DIMENSIONS],  # a hypercube over other settings is another sample
    }
    settings_path = out / "settings.json"
    if settings_path.exists() and json.loads(settings_path.read_text()) != settings:
        print(f"{out} holds a sweep run with {json.loads(settings_path.read_text())}, not {settings}: use another --out", file=sys.stderr)
        return 2
    settings_path.write_text(json.dumps(settings))
    points = sample(args.runs, args.seed)
    done = {row["index"] for row in load_rows(out) if "error" not in row}  # an errored point is run again
    jobs = [(i, p, args.seed * 100_000 + i, args.years, args.population, str(out)) for i, p in enumerate(points) if i not in done]
    print(f"{len(points)} points, {len(done)} already done, {len(jobs)} to run on {args.workers} workers", flush=True)
    context = multiprocessing.get_context("fork")
    try:
        with concurrent.futures.ProcessPoolExecutor(args.workers, mp_context=context) as pool, (out / "rows.jsonl").open("a") as sink:
            futures = [pool.submit(run_point, job) for job in jobs]
            for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
                sink.write(json.dumps(future.result()) + "\n")
                sink.flush()
                if n % 50 == 0:
                    print(f"  {n}/{len(jobs)}", flush=True)
    except concurrent.futures.process.BrokenProcessPool:
        print("a worker died (killed or out of memory): the rows written so far are kept, run again to resume", file=sys.stderr)
        return 1
    return report(args)


def describe(box: Box) -> str:
    cuts = []
    for name, cut in box.restrictions.items():
        if isinstance(cut[0], str):
            cuts.append(f"{name} in {{{', '.join(str(level) for level in cut)}}}")
        elif cut[1] == float("inf"):
            cuts.append(f"{name} >= {cut[0]:.3g}")
        elif cut[0] == float("-inf"):
            cuts.append(f"{name} <= {cut[1]:.3g}")
        else:
            cuts.append(f"{cut[0]:.3g} <= {name} <= {cut[1]:.3g}")
    return "; ".join(cuts) if cuts else "(no restriction)"


def boxes_for(rows: list[dict[str, Any]], label: str) -> list[str]:
    """One line per archetype that is frequent enough to read: its share, and the PRIM box over these rows."""
    counts = collections.Counter(r["archetype"] for r in rows)
    lines = [f"### {label} ({len(rows)} runs)", "", "| archetype | runs | share | box | support | density | coverage |", "|---|---:|---:|---|---:|---:|---:|"]
    for archetype, n in counts.most_common():
        share = n / len(rows)
        if share < NON_TRIVIAL or n < MIN_CLASS_ROWS:
            lines.append(f"| {archetype} | {n} | {share:.1%} | under {NON_TRIVIAL:.0%} of the runs or {MIN_CLASS_ROWS} runs: not read | | | |")
            continue
        box = prim([r["point"] for r in rows], [r["archetype"] == archetype for r in rows])
        if box is None:
            lines.append(f"| {archetype} | {n} | {share:.1%} | no box found | | | |")
        else:
            lines.append(f"| {archetype} | {n} | {share:.1%} | {describe(box)} | {box.support:.0%} | {box.density:.0%} (base {share:.0%}) | {box.coverage:.0%} |")
    return lines + [""]


def sensitivity(rows: list[dict[str, Any]]) -> list[str]:
    """The runs relabelled at other realignment thresholds: how many archetypes reach NON_TRIVIAL of the runs, and each count.
    The row is a run made under ARCHETYPE_VERSION's rules, so the shipped threshold's line equals the run's own labels."""
    lines = ["### Other realignment thresholds (the same runs, relabelled)", "", "| spreads | realignment | churn | alternation | stasis | archetypes at 5% or more |", "|---:|---:|---:|---:|---:|---:|"]
    for threshold in sorted({0.25, REALIGNMENT_SPREADS, 0.75, 1.0}):
        counts = collections.Counter(relabel(r, threshold) for r in rows)
        frequent = sum(n / len(rows) >= NON_TRIVIAL for n in counts.values())
        lines.append(f"| {threshold} | {counts['realignment']} | {counts['churn']} | {counts['alternation']} | {counts['stasis']} | {frequent} |")
    return lines + [""]


def report(args: argparse.Namespace) -> int:
    rows = load_rows(args.out)
    ok = [r for r in rows if "error" not in r]
    failed_runs = [r for r in rows if "error" in r]
    lines = [f"# Catalogue of scenarios: {len(rows)} runs ({len(ok)} read, {len(failed_runs)} errored)", ""]
    if failed_runs:
        lines += [f"Errors: {dict(collections.Counter(r['error'] for r in failed_runs).most_common(3))}", ""]
    if not ok:
        print("\n".join(lines))
        return 1
    in_band = [r for r in ok if not r["failed"]]
    frequent = [a for a, n in collections.Counter(r["archetype"] for r in ok).items() if n / len(ok) >= NON_TRIVIAL]
    lines += [
        f"Archetypes at {NON_TRIVIAL:.0%} or more of the runs: **{len(frequent)}** ({', '.join(sorted(frequent))}). "
        f"Inside the plausibility band: **{len(in_band)}** runs ({len(in_band) / len(ok):.1%}). "
        f"Checks failed: {dict(collections.Counter(c for r in ok for c in r['failed']).most_common())}.", "",
    ]
    lines += boxes_for(ok, "All runs")
    if len(in_band) >= MIN_BAND_ROWS:
        lines += boxes_for(in_band, "Inside the plausibility band")
    else:
        lines += [f"Inside the plausibility band there are {len(in_band)} runs, under {MIN_BAND_ROWS}: no band-only boxes.", ""]
    lines += sensitivity(ok)
    text = "\n".join(lines)
    (args.out / "report.md").write_text(text + "\n")
    print(text)
    return 0


def _positive(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"{text} is not a positive integer")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("run", "report"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--years", type=int, default=15)
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--workers", type=_positive, default=max(1, (multiprocessing.cpu_count() or 2) - 2))
    args = parser.parse_args(argv)
    return run(args) if args.command == "run" else report(args)


if __name__ == "__main__":
    sys.exit(main())
