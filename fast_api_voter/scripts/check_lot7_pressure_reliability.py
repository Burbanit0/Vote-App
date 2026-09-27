"""
scripts/check_lot7_pressure_reliability.py

v4 Lot 7's confirmatory reliability pass (dev-plan/merry-hugging-hamming.md,
Lot 7's own "Judgment calls" section): Lot 6's pre-flight spike
(check_lot6_batch_reliability.py) already covered a `pressure_action`-shaped
TOY schema at sizes 1/3/5/10 -- 8/8 clean -- which formally satisfied the
roadmap's Principal Risks gate before this lot started. But that toy schema
had a wrong motif set (Literal[301,303,304,305] -- 303 is a ResponseMotif,
not a PressureMotif) and never swept the batch sizes production chunks
actually use (20-25, via chunk_voters/llm.max_batch_size), and it carried no
per-citizen `available` acts list -- no prior decision type in this
codebase has had one. This script re-runs the sweep against the REAL
schema/prompt builders (llm_schemas.PressureBatch, llm_behavior_engine.
build_pressure_system_prompt/build_pressure_user_prompt), written first in
this lot's own branch, engine wiring (run_polity_simulation.py) written only
after these numbers land -- per the plan's own stated preference over
extending check_lot6_batch_reliability.py's toy-schema script with a real-
schema mode.

Sweeps sizes 1/5/20/25 x repeats 2 x two menu modalities (electoral_only,
where every citizen's `available` is [0,4]; full menu, where it varies per
citizen), reporting ok/finish_reason/elapsed plus the out-of-`available`
rate (an act outside a citizen's own frozen available list, live-resolved
by accountability.applicable_pressure_act in production, never grounds for
batch rejection here -- see run_one's own commentary) and the realized
act x motif contingency table.

Setup: same as check_lot6_batch_reliability.py (Ollama container running,
qwen3:8b pulled).

Usage:
    python fast_api_voter/scripts/check_lot7_pressure_reliability.py \
        --sizes 1 5 20 25 --repeats 2 \
        --results scripts/lot6_batch_reliability_results.md --append
"""
from __future__ import annotations

import argparse
import dataclasses
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import PolityConfig, PressureMenuConfig, load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import (  # noqa: E402
    LlmResponseError,
    OllamaJsonClient,
    decode_pressure_batch,
)
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _consulted(size: int) -> list[Citizen]:
    return [
        Citizen(
            citizen_id=200 + i,
            issue_positions=tuple((i * 0.037 + d * 0.017) % 1.0 for d in range(20)),
            issue_priorities=tuple(1.0 / 20 for _ in range(20)),
            blank_threshold=0.5,
            ambition_score=0.5,
        )
        for i in range(size)
    ]


def _contexts(consulted: list[Citizen], modality: str, target: int) -> dict[int, PressureContext]:
    contexts = {}
    for i, citizen in enumerate(consulted):
        if modality == "electoral_only":
            available: tuple[int, ...] = (0, 4)
            petition_open = False
        else:
            # Full menu: alternate the frozen state across the cohort so
            # the sweep actually exercises a varying available list, not
            # a uniform one -- the one empirical property this script
            # exists to test.
            if i % 3 == 0:
                available, petition_open = (0, 1, 3, 4), True
            elif i % 3 == 1:
                available, petition_open = (0, 2, 3, 4), False
            else:
                available, petition_open = (0, 3, 4), False
        contexts[citizen.citizen_id] = PressureContext(
            cid=citizen.citizen_id,
            target=target,
            self_gap=round(0.3 + (i % 5) * 0.08, 2),
            mandate_dev=0.41,
            ticks_to_election=9,
            available=available,
            petition_open=petition_open,
            petition_expires_at_tick=12 if petition_open else None,
            already_signed=False,
        )
    return contexts


def _menu_config(config: PolityConfig, modality: str) -> PressureMenuConfig:
    if modality == "electoral_only":
        return config.pressure_menu
    return dataclasses.replace(
        config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
    )


def run_one(client: OllamaJsonClient, config: PolityConfig, size: int, modality: str) -> dict[str, Any]:
    consulted = _consulted(size)
    target = 999
    contexts = _contexts(consulted, modality, target)
    pressure_menu = _menu_config(config, modality)
    system_config = dataclasses.replace(config, pressure_menu=pressure_menu)

    start = time.monotonic()
    try:
        raw = client.complete_json(
            system_prompt=build_pressure_system_prompt(consulted, system_config),
            user_prompt=build_pressure_user_prompt(consulted, contexts),
            json_schema=PRESSURE_JSON_SCHEMA,
            max_tokens=compute_max_tokens(size),
            think=False,
        )
    except Exception as exc:  # noqa: BLE001 -- spike script: report any transport failure shape
        elapsed = time.monotonic() - start
        return {"ok": False, "elapsed": elapsed, "reason": f"transport error: {exc}"}
    elapsed = time.monotonic() - start

    expected_cids = [c.citizen_id for c in consulted]
    try:
        decisions = decode_pressure_batch(raw, expected_cids)
    except LlmResponseError as exc:
        return {"ok": False, "elapsed": elapsed, "reason": f"decode failed: {exc}", "raw": raw[:500]}

    legal = menu_acts(pressure_menu)
    out_of_menu = [d for d in decisions if d.act not in legal]
    out_of_available = [d for d in decisions if d.act not in contexts[d.cid].available]
    act_motif_pairs = sorted({(d.act, d.motif) for d in decisions})

    ok = not out_of_menu
    return {
        "ok": ok,
        "elapsed": elapsed,
        "out_of_menu_count": len(out_of_menu),
        "out_of_available_count": len(out_of_available),
        "out_of_available_rate": round(len(out_of_available) / len(decisions), 3) if decisions else 0.0,
        "act_motif_pairs": act_motif_pairs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[1, 5, 20, 25])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--results", type=Path, default=None)
    parser.add_argument("--append", action="store_true", help="append to --results instead of overwriting")
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line, flush=True)
        lines.append(line)

    log("\n## Lot 7 confirmatory pass -- real pressure_action schema\n")
    log(
        "Real llm_schemas.PressureBatch / llm_behavior_engine.build_pressure_*_prompt, not the "
        "toy schema above (which had the wrong motif set -- 303 is a ResponseMotif -- and never "
        "carried a per-citizen `available` acts list). Sweeps the batch sizes chunk_voters actually "
        "produces (20-25), not just the pre-flight 1-10 range.\n"
    )
    log("| size | modality | rep | ok | elapsed(s) | out_of_available_rate | act x motif pairs | detail |")
    log("|---|---|---|---|---|---|---|---|")

    failure_count = 0
    total_count = 0

    config = load_config()
    with OllamaJsonClient.from_config(config.llm, seed=42) as client:
        for modality in ("electoral_only", "full_menu"):
            for size in args.sizes:
                for rep in range(1, args.repeats + 1):
                    result = run_one(client, config, size, modality)
                    total_count += 1
                    if not result["ok"]:
                        failure_count += 1
                    detail = result.get("reason", "")
                    log(
                        f"| {size} | {modality} | {rep} | {result['ok']} | {result['elapsed']:.1f} | "
                        f"{result.get('out_of_available_rate', 'n/a')} | "
                        f"{result.get('act_motif_pairs', 'n/a')} | {detail} |"
                    )

    log(f"\n### Summary\n\nfailures: {failure_count}/{total_count}")
    log(f"\n**Overall: {'PASS' if failure_count == 0 else 'FAIL'}**")

    if args.results:
        mode = "a" if args.append else "w"
        with args.results.open(mode, encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        log(f"\n(log {'appended to' if args.append else 'written to'} {args.results})")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
