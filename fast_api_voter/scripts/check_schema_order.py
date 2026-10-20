"""Choose the order each decision's fields are sent in, by measurement (ADR-030).

The model writes an object's fields in the order the schema sends them, and that order changes its answers
(EXP-025). Re-run this on a trigger only: a vLLM or xgrammar version, a model or quantisation, a decision class
gaining, losing or renaming a field, or a rewrite of a decision's system prompt.

Usage (from fast_api_voter/; `run` needs the vLLM server, the GPU and nothing else on it):
    python scripts/check_schema_order.py isolation              # no GPU: every arm changes key order only
    python scripts/check_schema_order.py run --out DIR \\
        --restart-between-controls "docker compose -f docker-compose.llm.yml restart vllm"
                                                                # two controls across a restart, one per candidate
    python scripts/check_schema_order.py decide --out DIR       # verdicts, results doc, proposed WIRE_ORDER

The controls send production's WIRE_ORDER; the candidates are the six orders of decision, dependents and
`motif` after the id (schema_order.RULES), plus alphabetical. A session is resumed if interrupted, so `run`
can be re-run after a crash. Then apply the proposed WIRE_ORDER by hand, re-run the live A/B
(scripts/schema_order_live_ab.sh), and commit the results doc with the change.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.bakeoff_bank import read_bank  # noqa: E402
from api.domain.polity.bakeoff_order import (  # noqa: E402
    ALPHA, NOISE_LIMIT, Verdict, decide, isolation_violations, proposed_table, recorded_order,
)
from api.domain.polity.bakeoff_runner import ARMS, GATES_FILENAME, RESULTS_FILENAME  # noqa: E402
from api.domain.polity.bakeoff_scorecard import load_session  # noqa: E402
from api.domain.polity.llm_client import WIRE_ORDER  # noqa: E402
from api.domain.polity.schema_order import RULES  # noqa: E402
from bakeoff_cases import ORDER_BANK  # noqa: E402

import run_bakeoff  # noqa: E402

CONTROLS = ("control-a", "control-b")
RESULTS_DOC = Path(__file__).resolve().parent / "check_schema_order_results.md"


def candidate_arms(control: Mapping[str, Sequence[str]]) -> list[str]:
    """Every candidate whose table is not the control's: today's WIRE_ORDER for `run`, and for `decide` whatever
    the control sessions recorded sending."""
    arms = ["alphabetical_order", *(f"order_{rule}" for rule in RULES)]
    wanted = {k: tuple(v) for k, v in control.items()}
    return [arm for arm in arms if {k: tuple(v) for k, v in (ARMS[arm].wire_order or {}).items()} != wanted]


def _healthy(base_url: str | None, timeout_s: float = 480.0) -> bool:
    url = (base_url or "http://localhost:8000/v1").removesuffix("/v1") + "/health"
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(2)
    return False


def _run(out: Path, base_url: str | None, restart: str | None) -> int:
    extra = ["--base-url", base_url] if base_url else []
    for label, arm in [*((c, None) for c in CONTROLS), *((a, a) for a in candidate_arms(WIRE_ORDER))]:
        if label == CONTROLS[1] and restart and not (out / label / GATES_FILENAME).is_file():
            # The two controls straddle a restart, so their difference covers what a new server instance changes:
            # on 2026-10-20 one thinking vote_cast case ran away after a restart, on identical bytes. Not again on a
            # resume once control-b is complete: other worktrees may be using the server.
            print(f"== restarting the server: {restart}", flush=True)
            if subprocess.run(restart, shell=True, check=False).returncode or not _healthy(base_url):
                print("the server did not come back")
                return 1
        print(f"== {label}", flush=True)
        code = run_bakeoff.main(["--label", label, "--bank", str(ORDER_BANK), "--out", str(out), *extra,
                                 *(["--arm", arm] if arm else [])])
        if code:
            return code
    return 0


def _fmt(order: tuple[str, ...]) -> str:
    return ", ".join(order)


def _table(order: Mapping[str, Sequence[str]]) -> str:
    return "; ".join(f"{title}: {', '.join(fields)}" for title, fields in sorted(order.items())) or "empty (all alphabetical)"


def report(verdicts: list[Verdict], bank_sha: str, sent: Mapping[str, Sequence[str]]) -> str:
    lines = [
        "# Field order per decision: the latest verdict (ADR-030)", "",
        f"The controls sent WIRE_ORDER {_table(sent)}. Production's WIRE_ORDER today: {_table(WIRE_ORDER)}."
        + ("" if {k: tuple(v) for k, v in sent.items()} == {k: tuple(v) for k, v in WIRE_ORDER.items()} else
           " They differ: this verdict is against the controls' order, not today's (ADR-030, \"The first table\")."), "",
        f"Written by `scripts/check_schema_order.py decide` on the order bank (`case_bank_order.jsonl`, sha "
        f"`{bank_sha[:16]}`). The rule, written before any run: a candidate replaces the current order only if it "
        f"beats the first control on the type's primary measure (paired McNemar, Holm across that type's "
        f"distinct candidate orders, p < {ALPHA}), also beats the second control, does not lower validity significantly and does "
        f"not collapse onto one answer; a measure whose two controls disagree on more than {NOISE_LIMIT:.0%} of "
        "units keeps the current order.", "",
        "| decision | primary measure | noise | current order | verdict | reason |", "| --- | --- | ---: | --- | --- | --- |",
    ]
    for v in verdicts:
        floor = "–" if v.noise is None else f"{v.noise:.1%}"
        change = "keep" if v.chosen == v.current else f"**{_fmt(v.chosen)}**"
        lines.append(f"| {v.decision_type} | {v.primary} | {floor} | {_fmt(v.current)} | {change} | {v.reason} |")
    for v in verdicts:
        if not v.candidates:
            continue
        lines += ["", f"## {v.decision_type}", "", "| candidate | order | score | control | 2nd control | better / worse | p (Holm) | failed |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
        lines += [f"| {c.rule} | {_fmt(c.order)} | {c.score}/{c.trials} | {c.control_score} | {c.control_b_score} | "
                  f"{c.first_only} / {c.second_only} | {c.p_holm:.3g} | {', '.join(c.failures) or '-'} |" for c in v.candidates]
    return "\n".join(lines) + "\n"


def _decide(out: Path) -> int:
    bank = read_bank(ORDER_BANK)
    sessions = {d.name: load_session(d) for d in sorted(out.iterdir()) if (d / RESULTS_FILENAME).is_file()}
    if any(c not in sessions for c in CONTROLS):
        print(f"missing control sessions in {out} -- run `run` first")
        return 1
    arms = candidate_arms(recorded_order(sessions[CONTROLS[1]]))
    missing = [arm for arm in arms if arm not in sessions]
    if missing:
        print(f"missing sessions in {out}: {', '.join(missing)} -- run `run` first")
        return 1
    candidates = {arm: (dict(ARMS[arm].wire_order or {}), sessions[arm]) for arm in arms}
    # control-b first: the candidates ran right after it, on its server instance; control-a replicates across the restart
    verdicts = decide(bank, (sessions[CONTROLS[1]], sessions[CONTROLS[0]]), candidates)
    sent = recorded_order(sessions[CONTROLS[1]])
    RESULTS_DOC.write_text(report(verdicts, bank.content_sha256, sent), encoding="utf-8")
    proposed = proposed_table(verdicts)
    print(f"wrote {RESULTS_DOC}")
    print("the controls' order stands" if proposed == sent else f"proposed WIRE_ORDER = {proposed!r}")
    if sent != {k: tuple(v) for k, v in WIRE_ORDER.items()}:
        print(f"note: these controls sent {sent!r}, not today's WIRE_ORDER; `run` into a new --out to measure against it")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("isolation", "run", "decide"))
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "bakeoff_runs" / "schema_order")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--restart-between-controls", metavar="CMD", default=None,
                        help='restart the server between the two controls (recommended: '
                             '"docker compose -f docker-compose.llm.yml restart vllm")')
    args = parser.parse_args(argv)
    if args.command == "isolation":
        violations = isolation_violations(read_bank(ORDER_BANK), candidate_arms({}) + ["alphabetical_order"])
        print("every arm changes key order only" if not violations else "CONTENT DIFFERS: " + "; ".join(violations))
        return 1 if violations else 0
    return _run(args.out, args.base_url, args.restart_between_controls) if args.command == "run" else _decide(args.out)


if __name__ == "__main__":
    raise SystemExit(main())
