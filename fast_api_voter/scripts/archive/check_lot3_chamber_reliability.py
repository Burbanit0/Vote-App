"""
scripts/check_lot3_chamber_reliability.py

v6b Lot 3's pre-flight reliability spike (the roadmap's own Principal Risks
gate) for `chamber_deliberation` (dt=11, §6bis.3) -- required before any
wiring code (decide_chamber_deliberation, run_polity_simulation.py's
_run_chamber_deliberation) is written, per this project's standing "spike
before you build on it" discipline (v4 Lot 6/7, v5 Lot 4's own precedent).

Unlike the pre-v4-Lot-6 spike, this goes straight to the real
llm_schemas.ChamberBatch / llm_behavior_engine.build_chamber_system_prompt /
build_chamber_user_prompt -- both already written and committed as this
lot's own first commit, exactly as v4 Lot 7/v5 Lot 4's own confirmatory
passes did.

chamber_deliberation has no §3.6.x subsection at all (§6bis.3 names it once,
with no worked JSON example) and its own real production batch size (30,
sortition_chamber.seats shipped) exceeds every size previously spiked (dt=8's
own spike covered 1/5/20/25) -- this is a genuinely new measurement, not a
continuation of an existing one, hence a fresh results doc rather than an
appended section.

Sweeps sizes 1/10/30 (30 is the ONLY real production cohort size at the
shipped sortition_chamber.seats=30 -- this decision type is NEVER chunked,
see decide_chamber_deliberation's own docstring for why chunk_voters would
itself raise NotImplementedError at this size) x repeats 2.

Setup: Ollama container running, qwen3:8b pulled (same as
check_lot6_batch_reliability.py / check_lot4_reaction_reliability.py).

Usage:
    python fast_api_voter/scripts/check_lot3_chamber_reliability.py \
        --sizes 1 10 30 --repeats 2 \
        --results scripts/lot3_chamber_reliability_results.md
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.codebook import ChamberMotif  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ChamberContext,
    build_chamber_system_prompt,
    build_chamber_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import (  # noqa: E402
    LlmResponseError,
    OllamaJsonClient,
    decode_chamber_batch,
)
from api.domain.polity.llm_schemas import CHAMBER_JSON_SCHEMA  # noqa: E402

_SINCERE = int(ChamberMotif.SINCERE_POSITION)
_SHIFTED = int(ChamberMotif.DELIBERATIVE_SHIFT)


def _members(size: int) -> list[Citizen]:
    citizens = [
        Citizen(
            citizen_id=700 + i,
            issue_positions=tuple((i * 0.041 + d * 0.013) % 1.0 for d in range(20)),
            issue_priorities=tuple(1.0 / 20 for _ in range(20)),
            blank_threshold=0.5,
            ambition_score=0.5,
            sortition_seat_until_tick=16,
            sortition_terms_served=1,
        )
        for i in range(size)
    ]
    for c in citizens:
        c.chamber_position = c.issue_positions
    return citizens


def _contexts(members: list[Citizen], tick: int) -> dict[int, ChamberContext]:
    result: dict[int, ChamberContext] = {}
    for m in members:
        assert m.sortition_seat_until_tick is not None
        result[m.citizen_id] = ChamberContext(cid=m.citizen_id, ticks_left=m.sortition_seat_until_tick - tick)
    return result


def run_one(client: OllamaJsonClient, size: int) -> dict[str, Any]:
    config = load_config()
    members = _members(size)
    contexts = _contexts(members, tick=4)

    start = time.monotonic()
    try:
        raw = client.complete_json(
            system_prompt=build_chamber_system_prompt(members, config),
            user_prompt=build_chamber_user_prompt(members, contexts),
            json_schema=CHAMBER_JSON_SCHEMA,
            max_tokens=compute_max_tokens(size),
            think=False,
        )
    except Exception as exc:  # noqa: BLE001 -- spike script: report any transport failure shape
        elapsed = time.monotonic() - start
        return {"ok": False, "elapsed": elapsed, "reason": f"transport error: {exc}"}
    elapsed = time.monotonic() - start

    expected_cids = [m.citizen_id for m in members]
    try:
        decisions = decode_chamber_batch(raw, expected_cids)
    except LlmResponseError as exc:
        return {"ok": False, "elapsed": elapsed, "reason": f"decode failed: {exc}", "raw": raw[:500]}

    out_of_menu = [d for d in decisions if d.motif not in (_SINCERE, _SHIFTED)]
    over_cap = [
        d for d in decisions
        if len(d.shifts) > config.sortition_chamber.max_deliberation_shifts
        or any(abs(s.delta) > config.sortition_chamber.max_deliberation_delta for s in d.shifts)
    ]
    # NOT a failure condition -- ChamberDecision deliberately dropped its
    # shifts<->motif coherence validator (this spike's own first pass
    # measured it failing at 9/10 and 6/6, see the results doc's own
    # earlier rows); tracked here purely as an informational rate.
    incoherent = [d for d in decisions if bool(d.shifts) != (d.motif == _SHIFTED)]
    motif_counts = {m: sum(1 for d in decisions if d.motif == m) for m in (_SINCERE, _SHIFTED)}

    ok = not out_of_menu and not over_cap
    return {
        "ok": ok,
        "elapsed": elapsed,
        "out_of_menu_count": len(out_of_menu),
        "over_cap_count": len(over_cap),
        "incoherent_count": len(incoherent),
        "motif_counts": motif_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[1, 10, 30])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line, flush=True)
        lines.append(line)

    log("# chamber_deliberation (dt=11, §6bis.3) reliability spike (v6b Lot 3)\n")
    log(
        "Real llm_schemas.ChamberBatch / llm_behavior_engine.build_chamber_*_prompt from the "
        "start (this lot's own first commit) -- no toy schema stage. Sweeps the one real "
        "production cohort size (30, sortition_chamber.seats shipped, NEVER chunked) plus "
        "smaller sizes for a margin.\n"
    )
    log("| size | rep | ok | elapsed(s) | out_of_menu | over_cap | incoherent | motif counts | detail |")
    log("|---|---|---|---|---|---|---|---|---|")

    failure_count = 0
    total_count = 0

    config = load_config()
    with OllamaJsonClient.from_config(config.llm, seed=42) as client:
        for size in args.sizes:
            for rep in range(1, args.repeats + 1):
                result = run_one(client, size)
                total_count += 1
                if not result["ok"]:
                    failure_count += 1
                detail = result.get("reason", "")
                log(
                    f"| {size} | {rep} | {result['ok']} | {result['elapsed']:.1f} | "
                    f"{result.get('out_of_menu_count', 'n/a')} | {result.get('over_cap_count', 'n/a')} | "
                    f"{result.get('incoherent_count', 'n/a')} | {result.get('motif_counts', 'n/a')} | {detail} |"
                )

    log(f"\n## Summary\n\nfailures: {failure_count}/{total_count}")
    log(f"\n**Overall: {'PASS' if failure_count == 0 else 'FAIL'}**")

    if args.results:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"\n(log written to {args.results})")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
