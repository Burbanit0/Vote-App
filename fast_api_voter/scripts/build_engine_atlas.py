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
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from api.domain.polity.events import INSTITUTIONAL_EVENT_TYPES  # noqa: E402
from api.domain.polity.run_catalog import DEFAULT_RUN_ROOT, parse_roots  # noqa: E402
from api.domain.polity.run_registry import discover_runs, run_record  # noqa: E402

ATLAS_DIR = Path(__file__).resolve().parent / "engine_atlas"
CONTENT = ATLAS_DIR / "content.json"
TEMPLATE = ATLAS_DIR / "template.html"
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
    """Every journaled event. A run still being written can end on a half-written line: that one is
    skipped (the next read has it whole); a broken line anywhere else is a broken journal and raises."""
    lines = [
        line
        for line in journal.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    events = [json.loads(line) for line in lines[:-1]]
    if lines:
        try:
            events.append(json.loads(lines[-1]))
        except ValueError:
            pass
    return events


def compact_run(run_dir: Path) -> dict[str, Any]:
    """The replay: every event with a one-line summary, the per-tick series, and the config (for a comparison)."""
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
        "config": config,
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
    for slot, data in (
        ("/*ATLAS_DATA*/{}", content),
        ("/*REPLAY_DATA*/{}", replay),
    ):
        if page.count(slot) != 1:
            raise ValueError(f"{slot} must appear exactly once in {TEMPLATE.name}")
        page = page.replace(slot, _embed(data))
    return page


def build(run_dir: Path, out: Path) -> Path:
    out.write_text(render_page(compact_run(run_dir)), encoding="utf-8")
    return out


# ── serving: every run, live ──────────────────────────────────────────────

LIVE_SECONDS = 600
"""A run with no digest whose journal or progress changed this recently is still running. progress.json is
rewritten at least every few seconds while LLM calls come back (progress._HEARTBEAT_MIN_WRITE_INTERVAL_SECONDS)
and at every tick, so ten quiet minutes means it stopped without a digest (killed, host down)."""
_WATCHED = ("events.jsonl", "progress.json", "digest.json")


def _stamp(run_dir: Path) -> tuple[str, float]:
    """A token that changes whenever a file the replay or the listing reads changes, and the latest mtime."""
    parts, latest = [], 0.0
    for name in _WATCHED:
        try:
            st = (run_dir / name).stat()
        except OSError:
            parts.append("-")
            continue
        parts.append(f"{st.st_mtime_ns}:{st.st_size}")
        latest = max(latest, st.st_mtime) if name != "digest.json" else latest
    return "/".join(parts), latest


def default_roots() -> list[Path]:
    configured = [
        root.path for root in parse_roots(os.environ.get("POLITY_RUN_ROOTS", ""))
    ]
    return configured or [DEFAULT_RUN_ROOT, BACKEND / "scripts"]


class RunIndex:
    """The runs under the roots, listed afresh on every call; a run is addressed by `<root index>:<relative
    path>` so a request never names a path the listing did not find. Each replay is rebuilt only when its
    files change."""

    def __init__(self, roots: list[Path]) -> None:
        self.roots = roots
        self.dirs: dict[str, Path] = {}
        self.cache: dict[str, tuple[str, bytes]] = {}

    def listing(self) -> list[dict[str, Any]]:
        now, runs, dirs = time.time(), [], {}
        for i, root in enumerate(self.roots):
            for run_dir in discover_runs([root]):
                key = f"{i}:{run_dir.relative_to(root).as_posix()}"
                dirs[key] = run_dir
                record, (stamp, mtime) = run_record(run_dir), _stamp(run_dir)
                progress = _json(run_dir / "progress.json") or {}
                reached, planned = (
                    record.get("ticks_reached"),
                    record.get("ticks_planned"),
                )
                status = record.get("outcome") or (
                    "live"
                    if now - mtime < LIVE_SECONDS
                    else "completed"
                    if reached is not None and reached == planned
                    else "stopped"
                )
                runs.append(
                    {
                        "key": key,
                        "root": str(root),
                        "path": key.split(":", 1)[1],
                        "run_id": record["run_id"],
                        "status": status,
                        "ticks_reached": reached,
                        "ticks_planned": planned,
                        "engine": record.get("engine"),
                        "model": record.get("model"),
                        "population": record.get("population"),
                        "years": record.get("years"),
                        "seed": record.get("seed"),
                        "mtime": mtime,
                        "stamp": stamp,
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
        stamp, _ = _stamp(run_dir)
        cached = self.cache.get(key)
        if cached is None or cached[0] != stamp:
            # ponytail: one whole re-read per change (0.4 s for the largest p500 journal); tail the file if runs grow far past that
            cached = (
                stamp,
                json.dumps(
                    compact_run(run_dir), separators=(",", ":"), ensure_ascii=False
                ).encode(),
            )
            self.cache[key] = cached
        return cached[1]


def make_handler(index: RunIndex) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server's name)
            path, _, query = self.path.partition("?")
            try:
                if path == "/":
                    self._send(200, "text/html", render_page(None).encode())
                elif path == "/runs":
                    self._send(
                        200, "application/json", json.dumps(index.listing()).encode()
                    )
                elif path == "/run":
                    body = index.replay(parse_qs(query).get("k", [""])[0])
                    if body is None:
                        self._send(404, "text/plain", b"no such run")
                    else:
                        self._send(200, "application/json", body)
                else:
                    self._send(404, "text/plain", b"not found")
            except Exception as error:  # a broken run answers 500 with its reason; the server keeps serving
                self._send(
                    500, "text/plain", f"{type(error).__name__}: {error}".encode()
                )

        def _send(self, code: int, kind: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", f"{kind}; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

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
