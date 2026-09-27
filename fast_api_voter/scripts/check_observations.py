"""Reproduces the numbers in docs/plan/polity/observations.md.

Each subcommand reads run files already on disk (or, for `kernels` and `term-limit`,
runs short CPU-only simulations with the test suite's fake model client) and prints
what an observation entry cites. Nothing here talks to a model server.

Usage (from fast_api_voter/):
    python scripts/check_observations.py elections scripts/seed_sweep_runs        # OBS-001, 002, 011, 013
    python scripts/check_observations.py requests <run_dir> --ticks 0 16           # OBS-001
    python scripts/check_observations.py truncations <run_dir>                     # OBS-008
    python scripts/check_observations.py chamber <run_dir>                         # OBS-004
    python scripts/check_observations.py kernels                                   # OBS-009 (~25 min, CPU)
    python scripts/check_observations.py term-limit                                # OBS-012

<run_dir> is the directory holding events.jsonl (and llm_calls.jsonl, for calls logged
since S0.5). A run still in progress can be read; a torn final line is skipped.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.domain.polity.checkpoint import load_checkpoint  # noqa: E402
from api.domain.polity.llm_time_attribution import kept_calls  # noqa: E402
from api.domain.polity.simple_rules import sympathizer_ratio  # noqa: E402

_KERNELS = ("default", "Haswell", "Sandybridge", "Nehalem", "Prescott")
_NOMINATION_CRITERIA = {206: "ambition", 207: "support", 208: "platform"}


def _jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _run_dirs(roots: list[Path]) -> list[Path]:
    return sorted({journal.parent for root in roots for journal in root.rglob("events.jsonl")})


# ── elections: OBS-001, OBS-002, OBS-011, OBS-013 ─────────────────────────

def _first_election_nominations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ticks = [e["tick"] for e in events if e["event_type"] == "party_nomination_choice"]
    return [e for e in events if e["event_type"] == "party_nomination_choice" and ticks and e["tick"] == min(ticks)]


def _nomination_rows(run_dir: Path, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Model-made nominations at the run's first election, ranked on each criterion the
    nomination prompt shows (ambition, perceived support, platform distance)."""
    state = load_checkpoint(run_dir / "checkpoint.json").state
    citizens = {c.citizen_id: c for c in state.citizens}
    platforms = {p.party_id: p.platform for p in state.parties}
    rows = []
    for event in _first_election_nominations(events):
        payload = event["payload"]
        if payload.get("llm_fallback"):
            continue
        members = sorted(payload["contenders"])
        values = {
            "ambition": {cid: -citizens[cid].ambition_score for cid in members},
            "support": {cid: -sympathizer_ratio(citizens[cid], state.citizens) for cid in members},
            "platform": {cid: math.dist(citizens[cid].issue_positions, platforms[payload["party_id"]]) for cid in members},
        }
        winner = event["citizen_id"]
        rows.append({
            "contenders": len(members),
            "position": members.index(winner) + 1,
            "motif": int(event["motif"]),
            **{name: sorted(members, key=by.__getitem__).index(winner) + 1 for name, by in values.items()},
        })
    return rows


def _election_summary(run_dir: Path) -> dict[str, Any]:
    events = list(_jsonl(run_dir / "events.jsonl"))
    field: dict[int, set[int]] = collections.defaultdict(set)
    declared: dict[int, set[int]] = collections.defaultdict(set)
    for event in events:
        if event["event_type"] == "candidacy_declared" and event["payload"].get("path") == "dominant":
            field[event["tick"]].add(event["citizen_id"])
        elif event["event_type"] == "candidacy_considered" and event["payload"].get("outcome") == 1:
            declared[event["tick"]].add(event["citizen_id"])
    winners = [e["citizen_id"] for e in events if e["event_type"] == "elected"]
    ticks = sorted(field)
    ambition = {c.citizen_id: c.ambition_score for c in load_checkpoint(run_dir / "checkpoint.json").state.citizens}
    first = min((e["tick"] for e in events if e["event_type"] == "candidacy_considered"), default=None)
    considered = [e for e in events if e["event_type"] == "candidacy_considered" and e["tick"] == first]
    return {
        "run": run_dir.name,
        "election_pairs": len(ticks) - 1,
        "same_field": sum(field[a] == field[b] for a, b in zip(ticks, ticks[1:])),
        "same_declared": sum(declared[a] == declared[b] for a, b in zip(ticks, ticks[1:])),
        "winner_pairs": len(winners) - 1,
        "winner_repeats": sum(a == b for a, b in zip(winners, winners[1:])),
        "considered": len(considered),
        "declared": sum(e["payload"]["outcome"] == 1 for e in considered),
        "above_threshold": sum(ambition[e["citizen_id"]] >= 0.3 for e in considered),
        "declared_above": sum(e["payload"]["outcome"] == 1 and ambition[e["citizen_id"]] >= 0.3 for e in considered),
        "nominations": _nomination_rows(run_dir, events),
    }


def _print_nominations(rows: list[dict[str, Any]]) -> None:
    print(f"\nFirst-election model nominations: {len(rows)}")
    for motif, criterion in _NOMINATION_CRITERIA.items():
        picks = [r for r in rows if r["motif"] == motif]
        best = sum(r[criterion] == 1 for r in picks)
        chance = sum(1 / r["contenders"] for r in picks)
        print(f"  motif {motif} ({criterion}): {len(picks)} picks, {best} best on that criterion (uniform choice: {chance:.1f})")
    last = sum(r["position"] == r["contenders"] for r in rows)
    print(f"  last listed position: {last} (uniform choice: {sum(1 / r['contenders'] for r in rows):.1f}); "
          f"first: {sum(r['position'] == 1 for r in rows)}")


def elections(roots: list[Path]) -> None:
    summaries = [_election_summary(run_dir) for run_dir in _run_dirs(roots) if (run_dir / "checkpoint.json").is_file()]
    print("| run | same field | same declared set | winner repeats | declared (first election) | ambition >= 0.3 | declared and >= 0.3 |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for s in summaries:
        print(f"| {s['run']} | {s['same_field']}/{s['election_pairs']} | {s['same_declared']}/{s['election_pairs']} | "
              f"{s['winner_repeats']}/{s['winner_pairs']} | {s['declared']}/{s['considered']} | {s['above_threshold']} | {s['declared_above']} |")
    total = {key: sum(s[key] for s in summaries) for key in summaries[0] if isinstance(summaries[0][key], int)} if summaries else {}
    print(f"\nPooled: {json.dumps(total)}")
    _print_nominations([row for s in summaries for row in s["nominations"]])


# ── requests: OBS-001 ─────────────────────────────────────────────────────

def requests(run_dir: Path, ticks: tuple[int, int]) -> None:
    """First-attempt model requests at one tick that are byte-identical to a request
    at another, per decision type, and how many of those got the same answer."""
    answers: dict[str, dict[int, dict[str, str | None]]] = collections.defaultdict(lambda: collections.defaultdict(dict))
    for call in _jsonl(run_dir / "llm_calls.jsonl"):
        if call["kind"] == "decision" and call["tick"] in ticks and not call["attempt"]:
            answers[call["decision_type"]][call["tick"]][call["request_sha256"]] = call.get("content")
    earlier, later = ticks
    for decision_type, by_tick in sorted(answers.items()):
        identical = by_tick[earlier].keys() & by_tick[later].keys()
        same_answer = sum(by_tick[earlier][sha] == by_tick[later][sha] for sha in identical)
        print(f"{decision_type}: tick {earlier} {len(by_tick[earlier])} requests, tick {later} {len(by_tick[later])}, "
              f"identical {len(identical)}, same answer {same_answer}")


# ── truncations: OBS-008 ──────────────────────────────────────────────────

_SENTENCE_END = re.compile(r"(?<=[.?!])\s+")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if len(s.strip()) > 40]


def truncations(run_dir: Path) -> None:
    # The calls the run kept: a resumed run's interrupted attempt is dropped for the ticks it ran again.
    calls = [c for c in kept_calls(_jsonl(run_dir / "llm_calls.jsonl")) if c["kind"] == "decision"]
    cut = [c for c in calls if c.get("finish_reason") == "length"]
    print(f"{len(cut)} of {len(calls)} decision calls hit the token budget")
    print("| decision type | tick | seconds | reasoning tokens | top sentence repeats | second half: distinct / total sentences |")
    print("|---|---:|---:|---:|---:|---:|")
    for call in cut:
        reasoning = call.get("reasoning") or ""
        top = collections.Counter(_sentences(reasoning)).most_common(1)
        half = _sentences(reasoning[len(reasoning) // 2:])
        print(f"| {call['decision_type']} | {call['tick']} | {call['latency_ms'] / 1000:.0f} | {call['reasoning_tokens']} | "
              f"{top[0][1] if top else 0} | {len(set(half))} / {len(half)} |")


# ── chamber: OBS-004 ──────────────────────────────────────────────────────

_POSITIONS_EQUAL = re.compile(
    r"sincere[_ ]position[^.\n]{0,40}(same as|identical|equal to)"
    r"|(same as|identical to|equal to)[^.\n]{0,25}(sincere|chamber)"
    r"|(identical|the same)[^.\n]{0,10}(positions|arrays)",
    re.IGNORECASE,
)


def chamber(run_dir: Path) -> None:
    decisions = [e for e in _jsonl(run_dir / "events.jsonl") if e["event_type"] == "chamber_deliberation"]
    motifs = collections.Counter((e["motif"], bool(e["payload"].get("llm_fallback"))) for e in decisions)
    print(f"{len(decisions)} chamber decisions; (motif, fallback) -> count: {dict(motifs)}")
    calls_path = run_dir / "llm_calls.jsonl"
    if not calls_path.is_file():
        return
    completed = [
        c for c in _jsonl(calls_path)
        if c["decision_type"] == "chamber_deliberation" and c["kind"] == "decision" and c.get("finish_reason") == "stop"
    ]
    equal = sum(bool(_POSITIONS_EQUAL.search(c.get("reasoning") or "")) for c in completed)
    shifted = sum('"motif": 702' in (c.get("content") or "") for c in completed)
    print(f"{len(completed)} completed chamber calls; reasoning notes identical positions in {equal}; answers with a 702: {shifted}")


# ── kernels: OBS-009 ──────────────────────────────────────────────────────

def _kernel_run(seed: int, population: int, engine: str) -> dict[str, Any]:
    """One 8-year run in this process; hashes of the raw and float-rounded journal and
    of every model request."""
    from api.domain.polity.run_polity_simulation import run_simulation
    from api.tests.polity_golden import RecordingClient, _journal_summary, _request_summary, golden_config
    from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient

    with tempfile.TemporaryDirectory() as tmp:
        config = golden_config(Path(tmp), llm=engine == "llm")
        config = dataclasses.replace(
            config,
            run=dataclasses.replace(config.run, seed=seed, population_size=population, duration_years=8),
            sortition_chamber=dataclasses.replace(config.sortition_chamber, seats=15),
            events=dataclasses.replace(config.events, scandal_rate_per_tick=0.05),
        )
        client = RecordingClient(_ElectingFakeLlmClient()) if engine == "llm" else None
        journal = run_simulation(config, run_id="kernel", llm_client=client)
        return {
            "raw": hashlib.sha256(journal.read_bytes()).hexdigest(),
            "rounded": _journal_summary(journal)["events_sha256"],
            "events": _journal_summary(journal)["event_count"],
            "requests": _request_summary(client.requests)["sequence_sha256"] if client else None,
        }


def kernels() -> None:
    shapes = [(seed, 100, engine) for engine in ("deterministic", "llm") for seed in range(1, 11)]
    shapes += [(seed, 500, engine) for engine in ("deterministic", "llm") for seed in (1, 2, 42)]
    differing = {"raw": 0, "rounded": 0, "requests": 0}
    for seed, population, engine in shapes:
        results = {}
        for kernel in _KERNELS:
            env = {**os.environ, "OPENBLAS_NUM_THREADS": "1"}
            env.pop("OPENBLAS_CORETYPE", None)
            if kernel != "default":
                env["OPENBLAS_CORETYPE"] = kernel
            out = subprocess.run(
                [sys.executable, __file__, "_kernel-run", str(seed), str(population), engine],
                env=env, capture_output=True, text=True, check=True,
            )
            results[kernel] = json.loads(out.stdout.strip().splitlines()[-1])
        distinct = {key: len({r[key] for r in results.values()}) for key in differing}
        for key, count in distinct.items():
            differing[key] += count > 1
        print(f"seed {seed} p{population} {engine}: {results['default']['events']} events, distinct across kernels {distinct}")
    print(f"\n{len(shapes)} shapes x {len(_KERNELS)} kernels; shapes whose hashes differ between kernels: {differing}")


# ── term-limit: OBS-012 ───────────────────────────────────────────────────

def term_limit() -> None:
    from api.domain.polity.run_polity_simulation import run_simulation
    from api.tests.polity_golden import golden_config
    from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient

    for engine in ("deterministic", "llm"):
        for limit in (None, 1):
            with tempfile.TemporaryDirectory() as tmp:
                config = golden_config(Path(tmp), llm=engine == "llm")
                config = dataclasses.replace(
                    config,
                    run=dataclasses.replace(config.run, seed=1, population_size=100, duration_years=8),
                    institutions=dataclasses.replace(config.institutions, president_term_limit=limit),
                )
                journal = run_simulation(config, run_id="term-limit", llm_client=_ElectingFakeLlmClient() if engine == "llm" else None)
                winners = [(e["tick"], e["citizen_id"]) for e in _jsonl(journal) if e["event_type"] == "elected"]
                print(f"{engine}, president_term_limit={limit}: {len({cid for _, cid in winners})} distinct presidents, elected {winners}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("elections").add_argument("roots", nargs="+", type=Path)
    requests_parser = sub.add_parser("requests")
    requests_parser.add_argument("run_dir", type=Path)
    requests_parser.add_argument("--ticks", nargs=2, type=int, default=(0, 16))
    sub.add_parser("truncations").add_argument("run_dir", type=Path)
    sub.add_parser("chamber").add_argument("run_dir", type=Path)
    sub.add_parser("kernels")
    sub.add_parser("term-limit")
    kernel_run = sub.add_parser("_kernel-run")
    kernel_run.add_argument("seed", type=int)
    kernel_run.add_argument("population", type=int)
    kernel_run.add_argument("engine", choices=("deterministic", "llm"))
    args = parser.parse_args(argv)

    if args.command == "elections":
        elections(args.roots)
    elif args.command == "requests":
        requests(args.run_dir, tuple(args.ticks))
    elif args.command == "truncations":
        truncations(args.run_dir)
    elif args.command == "chamber":
        chamber(args.run_dir)
    elif args.command == "kernels":
        kernels()
    elif args.command == "term-limit":
        term_limit()
    else:
        print(json.dumps(_kernel_run(args.seed, args.population, args.engine)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
