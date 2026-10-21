"""Build the polity engine atlas for a recorded run, and keep its code references honest.

The atlas is one standalone HTML page: the engine's modules and tick order, every mechanic (what it reads,
decides and writes, its knobs, its code), and the run replayed tick by tick. Its content lives in
scripts/engine_atlas/content.json; every code reference there names the line it points at and what that line
reads, and api/tests/test_polity_engine_atlas.py fails when one no longer matches.

Usage (from fast_api_voter/):
    python scripts/build_engine_atlas.py --run <run dir>            # writes <run dir>/engine_atlas.html
    python scripts/build_engine_atlas.py --run <run dir> --out atlas.html
    python scripts/build_engine_atlas.py --check                    # every reference still points at its line
    python scripts/build_engine_atlas.py --relocate                 # code only moved: update the line numbers
    python scripts/build_engine_atlas.py --serve [root ...]          # every run under the roots, live, A against B

A run dir is the one holding events.jsonl and config.json (e.g. polity_fixtures/runs/explorer-fixture, or a
sweep's <run>/run/<run>). digest.json, progress.json and run_metadata.json are used when present.

--serve opens the atlas on http://127.0.0.1:<port>/ (127.0.0.1 only) with a picker over every run found under the
roots (default: POLITY_RUN_ROOTS's paths, else the committed fixture and scripts/*_runs). A run still being
written is re-read whenever its files change, and the page follows it; a second run sets the comparison: its
series drawn dashed over the first, config differences, events per mechanic, and a B - A heatmap.

The crowd panel (plan-scenarios-v1, step 1b) draws every citizen on the population's own first two principal
axes at the selected tick, coloured by a lens, with the social graph's ties and a trail: frames come from the
yearly census (snapshots.jsonl) and, while the server watches a live run, from every tick's checkpoint.json,
which is rewritten each tick (run_polity_simulation) and is the only per-tick record of anger, engagement and
who mobilised. The panel lives in scripts/engine_atlas/crowd.html, injected at template.html's <!--CROWD-->.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Mapping, Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import numpy as np

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from api.domain.polity.config import SocialGraphConfig  # noqa: E402
from api.domain.polity.events import INSTITUTIONAL_EVENT_TYPES  # noqa: E402
from api.domain.polity.run_catalog import DEFAULT_RUN_ROOT, parse_roots  # noqa: E402
from api.domain.polity.run_projection import _pca  # noqa: E402
from api.domain.polity.run_registry import discover_runs, run_record  # noqa: E402
from api.domain.polity.social_graph import generate_social_graph  # noqa: E402

ATLAS_DIR = Path(__file__).resolve().parent / "engine_atlas"
CONTENT = ATLAS_DIR / "content.json"
TEMPLATE = ATLAS_DIR / "template.html"
CROWD = ATLAS_DIR / "crowd.html"
CROWD_SLOT = "<!--CROWD-->"
ACTS = {0: "nothing", 1: "sign", 2: "launch", 3: "mobilise", 4: "wait for election"}


def act_name(act: Any) -> str:
    return ACTS.get(act, str(act)) if isinstance(act, int) else str(act)


# ── code references ───────────────────────────────────────────────────────


def load_content() -> dict[str, Any]:
    content: dict[str, Any] = json.loads(CONTENT.read_text(encoding="utf-8"))
    return content


def code_refs(node: Any) -> list[dict[str, Any]]:
    """Every {file, line, expect} object in the content."""
    if isinstance(node, dict):
        if {"file", "line", "expect"} <= set(node):
            return [node]
        return [ref for value in node.values() for ref in code_refs(value)]
    if isinstance(node, list):
        return [ref for item in node for ref in code_refs(item)]
    return []


def source_path(file: str) -> Path:
    return BACKEND / (
        file if file.startswith(("scripts/", "api/")) else f"api/domain/polity/{file}"
    )


def _lines(file: str) -> list[str] | None:
    path = source_path(file)
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else None


def stale_refs(content: dict[str, Any]) -> list[str]:
    """Each reference whose file is gone or whose line no longer reads what it names."""
    stale = []
    for ref in code_refs(content):
        lines = _lines(ref["file"])
        line = (
            lines[ref["line"] - 1] if lines and 0 < ref["line"] <= len(lines) else None
        )
        if line is None or ref["expect"] not in line:
            stale.append(
                f"{ref['file']}:{ref['line']} no longer reads {ref['expect']!r}"
            )
    return stale


def relocate(content: dict[str, Any]) -> list[str]:
    """Move each stale reference to the one line that still reads what it names; return what cannot be moved."""
    unresolved = []
    for ref in code_refs(content):
        lines = _lines(ref["file"]) or []
        if 0 < ref["line"] <= len(lines) and ref["expect"] in lines[ref["line"] - 1]:
            continue
        found = [i for i, line in enumerate(lines, start=1) if ref["expect"] in line]
        if len(found) == 1:
            ref["line"] = found[0]
        else:
            unresolved.append(
                f"{ref['file']}:{ref['line']} {ref['expect']!r}: {len(found)} matching lines, fix it by hand"
            )
    return unresolved


# ── the run ───────────────────────────────────────────────────────────────


def _json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def summary(event: dict[str, Any]) -> str:
    """One line a person can read for one journaled event."""
    p, kind, cid = (
        event.get("payload") or {},
        event["event_type"],
        event.get("citizen_id"),
    )
    who = f"citizen {cid}" if cid is not None else "the polity"
    lines = {
        "pressure_action": lambda: (
            f"{who}: {act_name(p.get('act'))} (motif {event.get('motif')})"
        ),
        "elected": lambda: (
            f"citizen {cid} elected {p.get('office')}"
            + (
                f" ({p['abstained']} abstained)"
                if p.get("abstained") is not None
                else ""
            )
        ),
        "vote_cast": lambda: (
            f"{who} votes "
            + (
                "blank"
                if p.get("blank")
                else "ranking " + " > ".join(map(str, p.get("ranking", [])[:5]))
            )
        ),
        "candidacy_considered": lambda: (
            f"{who} {'declares' if p.get('outcome') else 'declines'} (motif {event.get('motif')})"
        ),
        "forum_post": lambda: (
            f"{who} posts; party move: {p.get('party_move') or 'none'}"
            + (
                f"; mind shifts on issue {p['shift_issue']}"
                if p.get("shift_issue") not in (-1, None)
                else ""
            )
        ),
        "party_founded": lambda: f"party {p.get('party_id')} founded ({_members(p)})",
        "party_dissolved": lambda: (
            f"party {p.get('party_id')} dissolved ({_members(p)})"
        ),
        "chamber_deliberation": lambda: (
            f"chamber member {cid}: motif {event.get('motif')} (deviation {p.get('chamber_deviation', 0):.2f})"
        ),
        "coalition_formed": lambda: (
            f"coalition of parties {', '.join(map(str, p.get('coalition', [])))}"
            + (
                f" after {p['rounds_used']} rounds"
                if p.get("rounds_used") is not None
                else ""
            )
        ),
        "coalition_decision": lambda: (
            f"party {p.get('party_id')} {'joins' if p.get('action') == 1 else 'stays out of'} party {p.get('initiator')}'s coalition"
            + (f" (round {p['round']})" if p.get("round") is not None else "")
            + (
                f", answered by its leader, citizen {p['leader']}"
                if p.get("leader") is not None
                else ""
            )
        ),
        "legislative_result": lambda: (
            "legislature: "
            + ", ".join(f"party {k} {v} seats" for k, v in _top_seats(p))
        ),
        "bill_proposed": lambda: (
            f"bill {p.get('bill_id')} proposed by party {p.get('proposer')} on issues {p.get('dimensions')}"
        ),
        "bill_voted": lambda: (
            f"bill {p.get('bill_id')} {'passes' if p.get('passed') else 'fails'}: {p.get('yes_seats')} yes / {p.get('no_seats')} no"
        ),
        "amendment_proposed": lambda: (
            f"amendment proposed on {p.get('article')} (now {p.get('old')})"
        ),
        "amendment_resolved": lambda: (
            f"amendment on {p.get('article')} {'ratified' if p.get('ratified') else 'rejected'}: {p.get('yes')}/{p.get('members')} yes"
        ),
        "constitution_amended": lambda: (
            f"constitution v{p.get('version')}: {p.get('article')} {p.get('old')} -> {p.get('new')}"
        ),
        "confidence_vote_triggered": lambda: (
            f"confidence vote on the {p.get('office')}: "
            + (
                "legitimacy fell below the floor"
                if p.get("cause") == "legitimacy_floor"
                else f"petition reached {p.get('signed_ratio', 0):.0%}"
            )
        ),
        "confidence_vote_result": lambda: (
            f"confidence vote: {p.get('keep')}/{p.get('ballots')} keep, {'retained' if p.get('retained') else 'recalled'}"
        ),
        "campaign_run": lambda: (
            f"nominee {cid} campaigns on issue {p.get('issue')} to the {p.get('audience')} ({p.get('citizens')} citizens moved)"
        ),
        "agent_turn": lambda: (
            f"{p.get('role', 'agent')} {cid}'s turn"
            + (
                f": “{(p.get('note_to_self') or '')[:90]}”"
                if p.get("note_to_self")
                else ""
            )
        ),
        "amendment_vote": lambda: (
            f"chamber member {cid} votes {p.get('vote', '?')} on {p.get('article')}"
        ),
        "sortition_rotation": lambda: (
            f"chamber reseated: {len(p.get('seated', []))} members drawn by lot"
        ),
        "legitimacy_updated": lambda: (
            f"legitimacy of the {p.get('office')}: {p.get('legitimacy', 0):.2f}"
        ),
    }
    if kind in ("petition_launched", "petition_signed", "petition_expired"):
        return f"{kind.replace('_', ' ')} against citizen {p.get('target', cid)}: {p.get('signed_ratio', 0):.0%} signed"
    if kind in lines:
        return str(lines[kind]())
    return str(kind).replace("_", " ") + (f" ({who})" if cid is not None else "")


def _members(payload: dict[str, Any]) -> str:
    n = payload.get("members")
    return f"{n} member{'' if n == 1 else 's'}"


def _top_seats(payload: dict[str, Any]) -> list[tuple[int, int]]:
    return sorted(
        ((int(k), v) for k, v in (payload.get("seats") or {}).items()),
        key=lambda kv: -kv[1],
    )[:4]


def _series(
    events: list[dict[str, Any]], ticks: int, initial_parties: int
) -> list[dict[str, Any]]:
    """Per tick: the president's legitimacy, mean emotions, engagement, opinion and policy drift, live parties, pressure acts."""
    fields: dict[
        str, dict[str, tuple[str, int | None]]
    ] = {  # event -> {series key: (payload key, rounding)}
        "emotions_updated": {f: (f, 3) for f in ("anger", "anxiety", "enthusiasm")},
        "engagement_updated": {
            "disengaged": ("disengaged", None),
            "exited": ("exited", None),
        },
        "opinion_dynamics_step": {"mean_shift": ("mean_shift", 4)},
        "policy_status": {"policy_distance": ("mean_citizen_distance", 3)},
    }
    rows: dict[int, dict[str, Any]] = collections.defaultdict(dict)
    acts: dict[int, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    births: collections.Counter[int] = collections.Counter()
    for e in events:
        t, p, kind = e["tick"], e.get("payload") or {}, e["event_type"]
        if kind in fields:
            rows[t].update(
                {
                    key: p[src] if digits is None else round(p[src], digits)
                    for key, (src, digits) in fields[kind].items()
                }
            )
        elif kind == "legitimacy_updated" and p.get("office") == "president":
            rows[t]["legitimacy"] = round(p["legitimacy"], 3)
        elif kind == "pressure_action":
            acts[t][act_name(p.get("act"))] += 1
        elif kind in ("party_founded", "party_dissolved"):
            births[t] += 1 if kind == "party_founded" else -1
    alive, out = initial_parties, []
    for t in range(ticks + 1):
        alive += births[t]
        out.append(
            {
                "tick": t,
                **rows.get(t, {}),
                "parties": alive,
                "acts": dict(acts.get(t, {})),
            }
        )
    return out


def read_events(journal: Path) -> list[dict[str, Any]]:
    """Every journaled event. A run still being written can end on a half-written line (no newline yet):
    that one is skipped, the next read has it whole. Any other broken line is a broken journal and raises."""
    text = journal.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    torn = bool(lines) and not text.endswith("\n")
    return [json.loads(line) for line in (lines[:-1] if torn else lines)] + (
        _whole_or_nothing(lines[-1]) if torn else []
    )


def _whole_or_nothing(line: str) -> list[dict[str, Any]]:
    try:
        return [json.loads(line)]
    except ValueError:
        return []


def compact_run(run_dir: Path) -> dict[str, Any]:
    """The replay: every event with a one-line summary, and the per-tick series."""
    events = read_events(run_dir / "events.jsonl")
    config = _json(run_dir / "config.json") or {}
    digest, progress, metadata = (
        _json(run_dir / name) or {}
        for name in ("digest.json", "progress.json", "run_metadata.json")
    )
    run = config.get("run", {})
    ticks = max((e["tick"] for e in events), default=0)
    initial_parties = int(config.get("parties", {}).get("initial_count", 0))
    meta = {
        "run_id": metadata.get("run_id")
        or (events[0]["run_id"] if events else run_dir.name),
        "source": str(run_dir),
        "ticks": ticks,
        "ticks_per_year": run.get("ticks_per_year", 4),
        "population": run.get("population_size"),
        "years": run.get("duration_years"),
        "engine": "llm" if config.get("llm", {}).get("enabled") else "deterministic",
        "model": config.get("llm", {}).get("model"),
        "provider": config.get("llm", {}).get("provider"),
        "initial_parties": initial_parties,
        "llm_decisions": dict(
            collections.Counter(
                e["event_type"] for e in events if e.get("codebook_version")
            )
        ),
        "llm_retries": progress.get("retry_count", digest.get("llm_retries")),
        "llm_fallbacks": progress.get("fallback_count", digest.get("llm_fallbacks")),
        "office_occupancy": digest.get("office_occupancy"),
        "effective_parties": digest.get("effective_parties"),
        "terms": digest.get("terms", []),
        "elapsed_hours": round(digest["elapsed_seconds"] / 3600, 2)
        if digest.get("elapsed_seconds")
        else None,
    }
    return {
        "meta": meta,
        "series": _series(events, ticks, initial_parties),
        "events": [
            {
                "id": e["event_id"],
                "t": e["tick"],
                "ty": e["event_type"],
                "c": e.get("citizen_id"),
                "m": e.get("motif"),
                "s": summary(e),
                **(
                    {"r": (e.get("payload") or {}).get("role")}
                    if e["event_type"] == "agent_turn"
                    else {}
                ),
            }
            for e in events
        ],
    }


# ── the crowd (plan-scenarios-v1, step 1b) ────────────────────────────────

CROWD_FIELDS = ("party_affiliation", "office", "anger", "engagement", "event_salience")
Frame = dict[str, Any]
CrowdState = dict[str, Any]
"""Per run: {"frames": {tick: Frame}, "edges": list | None}; the server keeps one for the run's life."""


def crowd_frame(citizens: Sequence[Mapping[str, Any]], tick: int, acted: Mapping[Any, Any] | None = None) -> Frame:
    """One tick of the crowd, citizens in id order: the issue positions and the fields a lens colours by. A
    field the source lacks is None for the whole frame (the yearly census carries no emotions; a checkpoint
    writes anger and engagement only once they are tracked). `acted` is the checkpoint's mobilized_last_tick."""
    ordered = sorted(citizens, key=lambda c: int(c["citizen_id"]))
    frame: Frame = {
        "tick": tick,
        "positions": [[float(x) for x in c["issue_positions"]] for c in ordered],
        "acted": sorted(int(i) for i in (acted or {})),
    }
    for field in CROWD_FIELDS:
        values = [c.get(field) for c in ordered]
        frame[field.removeprefix("event_").removesuffix("_affiliation")] = values if any(v is not None for v in values) else None
    return frame


def _checkpoint(run_dir: Path) -> dict[str, Any] | None:
    """The run's checkpoint. save_checkpoint writes it whole (a temp file, then os.replace), so a torn read is
    not expected; a run dir edited by hand gets None and the next read, not a dead replay."""
    try:
        return _json(run_dir / "checkpoint.json")
    except ValueError:
        return None


def collect_frames(run_dir: Path, frames: dict[int, Frame], population: int | None) -> None:
    """Add to `frames` (tick -> frame) every whole census tick it lacks and the checkpoint's tick. The census
    is appended one citizen at a time, so a tick is taken only once all `population` rows are there (a short
    read would stay for the server's life). The checkpoint is the richer source for its tick (emotions, who
    mobilised) and the only one that moves between censuses, so a live run's history is what the server saw
    while it watched, plus the census for what it missed."""
    census = run_dir / "snapshots.jsonl"
    if census.is_file():
        # ponytail: the whole census is parsed on every change (about 50 ms for 15k rows); tail it if that shows
        by_tick: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
        for row in read_events(census):
            by_tick[int(row["tick"])].append(row)
        for tick, rows in by_tick.items():
            if tick not in frames and (population is None or len(rows) == population):
                frames[tick] = crowd_frame(rows, tick)
    checkpoint = _checkpoint(run_dir)
    if checkpoint and checkpoint.get("citizens"):
        tick = int(checkpoint["tick"])
        frames[tick] = crowd_frame(checkpoint["citizens"], tick, checkpoint.get("mobilized_last_tick"))


def _edges(config: Mapping[str, Any]) -> list[list[int]]:
    """The social graph's ties, regenerated from the config (the graph is deterministic in config, population
    and seed, and is deliberately not checkpointed); none when the graph is off."""
    graph, run = config.get("social_graph") or {}, config.get("run") or {}
    fields = [f.name for f in dataclasses.fields(SocialGraphConfig)]
    if not graph.get("enabled") or not {"population_size", "seed"} <= set(run) or not set(fields) <= set(graph):
        return []  # the ties are decoration: a config this code cannot read loses them, not the replay
    ties = generate_social_graph(SocialGraphConfig(**{f: graph[f] for f in fields}), int(run["population_size"]), int(run["seed"]))
    return sorted([i, j] for i, neighbours in ties.neighbors.items() for j in neighbours if i < j)


def crowd_payload(run_dir: Path, state: CrowdState) -> dict[str, Any]:
    """What the crowd panel draws: the frames projected on the first frame's axes (run_projection's PCA, signed
    the same way from one run to the next so run B is not run A's mirror), the ties, the ticks. `state` keeps
    the frames and the ties between calls."""
    config = _json(run_dir / "config.json") or {}
    population = (config.get("run") or {}).get("population_size")
    frames: dict[int, Frame] = state.setdefault("frames", {})
    collect_frames(run_dir, frames, None if population is None else int(population))
    if not frames:
        return {"ticks": [], "frames": {}, "edges": []}
    if state.get("edges") is None:
        state["edges"] = _edges(config)
    mean, axes = _pca(np.array(frames[min(frames)]["positions"], dtype=float))
    projected = {}
    for tick, frame in sorted(frames.items()):
        xy = (np.array(frame["positions"], dtype=float) - mean) @ axes.T
        projected[str(tick)] = {k: v for k, v in frame.items() if k != "positions"} | {"xy": np.round(xy, 3).tolist()}
    return {"ticks": sorted(frames), "frames": projected, "edges": state["edges"]}


# ── the page ──────────────────────────────────────────────────────────────


def commit() -> str:
    """The commit the code references link to on GitHub (they 404 until it is pushed)."""
    done = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.strip() if done.returncode == 0 else "polity"


def _embed(data: Any) -> str:
    """JSON written into the page's script as a JS value (JSON is a subset of JS), safe inside a
    <script> element: no `<` (so no `</script>`, `<!--` or `<script>`), `>` or `&` as such."""
    text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_page(replay: dict[str, Any] | None) -> str:
    """The page, with the run embedded; None leaves the replay to the server (--serve), which the page fetches."""
    content = {
        **load_content(),
        "sha": commit(),
        "institutional": sorted(INSTITUTIONAL_EVENT_TYPES),
    }
    page = TEMPLATE.read_text(encoding="utf-8")
    for slot, text in (
        ("/*ATLAS_DATA*/{}", _embed(content)),
        ("/*REPLAY_DATA*/{}", _embed(replay)),
        (CROWD_SLOT, CROWD.read_text(encoding="utf-8")),
    ):
        if page.count(slot) != 1:
            raise ValueError(f"{slot} must appear exactly once in {TEMPLATE.name}")
        page = page.replace(slot, text)
    return page


def build(run_dir: Path, out: Path) -> Path:
    out.write_text(render_page({**compact_run(run_dir), "crowd": crowd_payload(run_dir, {})}), encoding="utf-8")
    return out


# ── serving: every run, live ──────────────────────────────────────────────

LIVE_SECONDS = 600
"""A run with no digest whose journal or progress changed this recently is still running. progress.json is
rewritten at least every few seconds while LLM calls come back (progress._HEARTBEAT_MIN_WRITE_INTERVAL_SECONDS)
and at every tick, so ten quiet minutes means it stopped without a digest (killed, host down)."""


def _stat(path: Path) -> os.stat_result | None:
    try:
        return path.stat()
    except OSError:
        return None


def _stamp(run_dir: Path) -> str:
    """Changes whenever a file the replay reads changes: the journal, the digest, and the checkpoint the crowd
    panel reads (rewritten once a tick). Not progress.json: its heartbeat rewrites it every few seconds with
    no new event, and the replay only takes two counters from it."""
    stats = (_stat(run_dir / name) for name in ("events.jsonl", "digest.json", "checkpoint.json"))
    return "/".join(f"{st.st_mtime_ns}:{st.st_size}" if st else "-" for st in stats)


def _written(run_dir: Path) -> float:
    """When the run last wrote its journal or its progress (the heartbeat counts: the run is alive)."""
    stats = [_stat(run_dir / name) for name in ("events.jsonl", "progress.json")]
    return max((st.st_mtime for st in stats if st), default=0.0)


def run_status(record: dict[str, Any], progress: dict[str, Any], written: float) -> str:
    """The digest's outcome; without one, live while the run is still writing and not done, else completed
    (every planned tick journaled, none under way) or stopped."""
    reached, planned = record.get("ticks_reached"), record.get("ticks_planned")
    done = (
        reached is not None
        and reached == planned
        and progress.get("tick_in_progress") is None
    )
    if record.get("outcome"):
        return str(record["outcome"])
    if done:
        return "completed"
    return "live" if time.time() - written < LIVE_SECONDS else "stopped"


def default_roots() -> list[Path]:
    configured = [
        root.path for root in parse_roots(os.environ.get("POLITY_RUN_ROOTS", ""))
    ]
    return configured or [DEFAULT_RUN_ROOT, *sorted(BACKEND.glob("scripts/*_runs"))]


class RunIndex:
    """The runs under the roots, listed afresh on every call; a run is addressed by `<root index>:<relative
    path>` so a request never names a path the listing did not find. Each replay is rebuilt only when its
    files change."""

    def __init__(self, roots: list[Path]) -> None:
        self.roots = roots
        self.dirs: dict[str, Path] = {}
        self.cache: dict[str, tuple[str, bytes]] = {}
        self.crowd: dict[str, CrowdState] = {}
        """Per run, the crowd frames seen so far and its ties (crowd_payload): a live run's per-tick history."""
        self.lock = threading.Lock()
        """One rebuild at a time: request threads share the cache and the crowd state."""

    def listing(self) -> list[dict[str, Any]]:
        runs, dirs = [], {}
        for i, root in enumerate(self.roots):
            for run_dir in discover_runs([root]):
                key = f"{i}:{run_dir.relative_to(root).as_posix()}"
                dirs[key] = run_dir
                record, written = run_record(run_dir), _written(run_dir)
                progress = _json(run_dir / "progress.json") or {}
                reached, planned = (
                    record.get("ticks_reached"),
                    record.get("ticks_planned"),
                )
                runs.append(
                    {
                        "key": key,
                        "root": str(root),
                        "path": key.split(":", 1)[1],
                        "run_id": record["run_id"],
                        "status": run_status(record, progress, written),
                        "ticks_reached": reached,
                        "ticks_planned": planned,
                        "engine": record.get("engine"),
                        "model": record.get("model"),
                        "population": record.get("population"),
                        "years": record.get("years"),
                        "seed": record.get("seed"),
                        "mtime": written,
                        "stamp": _stamp(run_dir),
                        "eta": progress.get("eta_timestamp"),
                        "tick_in_progress": progress.get("tick_in_progress"),
                    }
                )
        self.dirs = dirs
        return sorted(runs, key=lambda r: -r["mtime"])

    def replay(self, key: str) -> bytes | None:
        if key not in self.dirs:
            self.listing()
        run_dir = self.dirs.get(key)
        if run_dir is None:
            return None
        with self.lock:
            stamp = _stamp(run_dir)
            cached = self.cache.get(key)
            if cached is None or cached[0] != stamp:
                # ponytail: one whole re-read per change (0.4 s for the largest p500 journal); tail the file if runs grow far past that
                # The config rides only here, for the comparison: a static page is shared, and a config can hold URLs.
                replay = {
                    **compact_run(run_dir),
                    "config": _json(run_dir / "config.json") or {},
                    "crowd": crowd_payload(run_dir, self.crowd.setdefault(key, {})),
                }
                cached = (
                    stamp,
                    json.dumps(replay, separators=(",", ":"), ensure_ascii=False).encode(),
                )
                self.cache[key] = cached
            return cached[1]


def make_handler(index: RunIndex) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server's name)
            try:
                code, kind, body = self._answer()
            except Exception as error:  # a broken run answers 500 with its reason; the server keeps serving
                code, kind, body = (
                    500,
                    "text/plain",
                    f"{type(error).__name__}: {error}".encode(),
                )
            try:
                self.send_response(code)
                self.send_header("Content-Type", f"{kind}; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (
                BrokenPipeError,
                ConnectionResetError,
            ):  # the viewer left mid-download
                pass

        def _answer(self) -> tuple[int, str, bytes]:
            path, _, query = self.path.partition("?")
            if path == "/":
                return 200, "text/html", render_page(None).encode()
            if path == "/runs":
                return 200, "application/json", json.dumps(index.listing()).encode()
            if path == "/run":
                body = index.replay(parse_qs(query).get("k", [""])[0])
                return (
                    (404, "text/plain", b"no such run")
                    if body is None
                    else (200, "application/json", body)
                )
            return 404, "text/plain", b"not found"

        def log_message(
            self, format: str, *args: Any
        ) -> None:  # the page polls every few seconds
            pass

    return Handler


def serve(roots: list[Path], port: int, open_browser: bool) -> None:
    index = RunIndex(roots)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(index))
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(
        f"engine atlas on {url} ({len(index.listing())} runs under {', '.join(map(str, roots))}); Ctrl-C stops it",
        flush=True,
    )
    if open_browser:
        webbrowser.open(url + "#replay")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--run", type=Path, help="a run dir (holds events.jsonl and config.json)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="where to write the page (default: <run dir>/engine_atlas.html)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="only check that every code reference still points at its line",
    )
    parser.add_argument(
        "--relocate",
        action="store_true",
        help="update the line numbers of references whose code only moved",
    )
    parser.add_argument(
        "--serve",
        nargs="*",
        type=Path,
        metavar="ROOT",
        help="serve every run under these roots, live, with a comparison (default roots: see above)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="--serve's port (default 8765, 0 picks one)",
    )
    parser.add_argument(
        "--no-open", action="store_true", help="--serve without opening a browser"
    )
    args = parser.parse_args(argv)
    if args.relocate:
        content = load_content()
        unresolved = relocate(content)
        CONTENT.write_text(
            json.dumps(content, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print("\n".join(unresolved) or "every reference points at its line")
        return 1 if unresolved else 0
    stale = stale_refs(load_content())
    if (
        stale and args.serve is not None and not args.check
    ):  # debugging mid-edit: say so, keep serving
        print(
            "\n".join(stale)
            + "\nsome code links point at moved lines: run --relocate once the code settles",
            flush=True,
        )
    elif args.check or stale:
        print("\n".join(stale) or "every reference points at its line")
        if stale:
            print("run with --relocate if the code only moved")
        return 1 if stale else 0
    if args.serve is not None:
        serve(
            [root.expanduser().resolve() for root in args.serve] or default_roots(),
            args.port,
            not args.no_open,
        )
        return 0
    if args.run is None:
        parser.error("--run or --serve is required")
    if not (args.run / "events.jsonl").is_file():
        parser.error(f"{args.run} holds no events.jsonl: pass the run's own directory")
    print(build(args.run, args.out or args.run / "engine_atlas.html"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
