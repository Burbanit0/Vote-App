"""
scripts/check_lot4_reaction_reliability.py

v5 Lot 4's pre-flight reliability spike (the roadmap's own Principal Risks
gate) for `reaction_to_event` (dt=8, §8) -- required before any wiring code
(decide_reaction_to_event, run_polity_simulation.py's _run_reaction_to_event)
is written, per this project's standing "spike before you build on it"
discipline (v4 Lot 6/7's own precedent).

Unlike the pre-v4-Lot-6 spike, which had to invent TOY Pydantic schemas
because ResponseDecision/PressureDecision didn't exist yet (and got a real
motif set wrong as a result -- its toy PressureActionDecision.motif included
303, a ResponseMotif, not a PressureMotif), dt=8's real enums (EventType,
ReactionMotif) and its real schema (llm_schemas.ReactionBatch) have been
shipped and fully documented since v5 Lot 1/this lot's own first commit --
there is no reason to build a toy schema at all. This script goes straight
to the real llm_schemas.ReactionBatch / llm_behavior_engine.build_reaction_
system_prompt / build_reaction_user_prompt, exactly as v4 Lot 7's own
confirmatory pass did for pressure_action.

Sweeps sizes 1/5/25 (25 is the ONLY real production chunk size at shipped
population_size=100/llm.max_batch_size=25 -- 100/25 divides evenly with no
remainder, so unlike dt=10's variable consulted-cohort range, dt=8 has
exactly one real chunk size to confirm) x repeats 2 x both event types
(SCANDAL restricts the legal motif set to {401,403}, ECONOMIC_SHOCK to
{402,403} -- independent evidence needed for each, since the prompt/schema
shape differs by which motifs are shown as legal).

Setup: Ollama container running, qwen3:8b pulled (same as check_lot6_batch_
reliability.py / check_lot7_pressure_reliability.py).

Usage:
    python fast_api_voter/scripts/check_lot4_reaction_reliability.py \
        --sizes 1 5 25 --repeats 2 \
        --results scripts/lot4_reaction_reliability_results.md
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.codebook import EventType, ReactionMotif  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ReactionContext,
    build_reaction_system_prompt,
    build_reaction_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import (  # noqa: E402
    LlmResponseError,
    OllamaJsonClient,
    decode_reaction_batch,
)
from api.domain.polity.llm_schemas import REACTION_JSON_SCHEMA  # noqa: E402

_GROUNDING_MOTIF = {
    EventType.SCANDAL: ReactionMotif.SCANDAL_TRUST_EROSION,
    EventType.ECONOMIC_SHOCK: ReactionMotif.ECONOMIC_SHOCK_REACTION,
}


def _citizens(size: int) -> list[Citizen]:
    return [
        Citizen(
            citizen_id=300 + i,
            issue_positions=tuple((i * 0.037 + d * 0.017) % 1.0 for d in range(20)),
            issue_priorities=tuple(1.0 / 20 for _ in range(20)),
            blank_threshold=0.5,
            ambition_score=0.5,
            event_salience=round((i % 5) * 0.1, 2),
        )
        for i in range(size)
    ]


def _contexts(citizens: list[Citizen]) -> dict[int, ReactionContext]:
    return {c.citizen_id: ReactionContext(cid=c.citizen_id, event_salience=c.event_salience) for c in citizens}


def run_one(client: OllamaJsonClient, event_type: EventType, size: int) -> dict[str, Any]:
    config = load_config()
    citizens = _citizens(size)
    contexts = _contexts(citizens)
    target = 999 if event_type is EventType.SCANDAL else None
    magnitude = 0.7 if event_type is EventType.ECONOMIC_SHOCK else 0.0

    start = time.monotonic()
    try:
        raw = client.complete_json(
            system_prompt=build_reaction_system_prompt(citizens, event_type, config),
            user_prompt=build_reaction_user_prompt(
                citizens, contexts, event_type=event_type, target=target, magnitude=magnitude
            ),
            json_schema=REACTION_JSON_SCHEMA,
            max_tokens=compute_max_tokens(size),
            think=False,
        )
    except Exception as exc:  # noqa: BLE001 -- spike script: report any transport failure shape
        elapsed = time.monotonic() - start
        return {"ok": False, "elapsed": elapsed, "reason": f"transport error: {exc}"}
    elapsed = time.monotonic() - start

    expected_cids = [c.citizen_id for c in citizens]
    try:
        decisions = decode_reaction_batch(raw, expected_cids)
    except LlmResponseError as exc:
        return {"ok": False, "elapsed": elapsed, "reason": f"decode failed: {exc}", "raw": raw[:500]}

    grounding = int(_GROUNDING_MOTIF[event_type])
    irrelevant = int(ReactionMotif.EVENT_PERSONALLY_IRRELEVANT)
    out_of_menu = [d for d in decisions if d.motif not in (grounding, irrelevant)]
    over_cap = [d for d in decisions if d.salience_delta > config.events.max_reaction_delta]
    incoherent = [d for d in decisions if (d.salience_delta == 0.0) != (d.motif == irrelevant)]
    motif_counts = {m: sum(1 for d in decisions if d.motif == m) for m in (grounding, irrelevant)}

    ok = not out_of_menu and not over_cap and not incoherent
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
    parser.add_argument("--sizes", type=int, nargs="+", default=[1, 5, 25])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line, flush=True)
        lines.append(line)

    log("# reaction_to_event (dt=8, §8) reliability spike (v5 Lot 4)\n")
    log(
        "Real llm_schemas.ReactionBatch / llm_behavior_engine.build_reaction_*_prompt, real "
        "EventType/ReactionMotif enums from the start (shipped since v5 Lot 1) -- no toy schema "
        "stage, unlike the pre-v4-Lot-6 spike. Sweeps the one real production chunk size (25, "
        "since 100/25 divides evenly with no remainder) plus smaller sizes for a margin.\n"
    )
    log("| event_type | size | rep | ok | elapsed(s) | out_of_menu | over_cap | incoherent | motif counts | detail |")
    log("|---|---|---|---|---|---|---|---|---|---|")

    failure_count = 0
    total_count = 0

    config = load_config()
    with OllamaJsonClient.from_config(config.llm, seed=42) as client:
        for event_type in (EventType.SCANDAL, EventType.ECONOMIC_SHOCK):
            for size in args.sizes:
                for rep in range(1, args.repeats + 1):
                    result = run_one(client, event_type, size)
                    total_count += 1
                    if not result["ok"]:
                        failure_count += 1
                    detail = result.get("reason", "")
                    log(
                        f"| {event_type.name} | {size} | {rep} | {result['ok']} | {result['elapsed']:.1f} | "
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
