"""
scripts/check_vllm_axis_b_chamber_sincere_position.py

plan-vllm-switch-readiness.md's axis (b), point 2: does the 2026-08-29 disambiguation fix to
build_chamber_system_prompt still prevent chamber_deliberation's Mode A non-terminating-reasoning
loop under vLLM's AWQ-quantized Qwen3-8B-AWQ? That fix was validated live on Ollama's un-quantized
qwen3:8b at 0/7 (plan-vllm-switch-readiness.md section 2, point 2) against `chamber_position ==
sincere_position` -- the normal state of any freshly-sortitioned or never-deviated member, not a
rare edge case (lot3_chamber_reliability_results.md: 7/270 live sweep, always this exact state).

Reuses production's real call shape exactly: single-member chunks (_CHAMBER_MAX_CHUNK_SIZE=1,
llm_behavior_engine.py), think=True, compute_max_tokens(1) + _CHAMBER_THINK_TOKEN_ALLOWANCE (8000),
real build_chamber_system_prompt/build_chamber_user_prompt -- not check_lot3_chamber_reliability.py's
own think=False pre-flight-spike shape (superseded in production by the think=True fix documented
in decide_chamber_deliberation's own docstring).

Usage:
    docker compose -f docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_axis_b_chamber_sincere_position.py
"""
from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

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
from api.domain.polity.llm_client import LlmResponseError, VllmJsonClient, decode_chamber_batch  # noqa: E402
from api.domain.polity.llm_schemas import CHAMBER_JSON_SCHEMA  # noqa: E402

_REPS = 10  # matching the live-validated Ollama bar's own order of magnitude (0/7)
_CHAMBER_THINK_TOKEN_ALLOWANCE = 8000
_SINCERE = int(ChamberMotif.SINCERE_POSITION)
_SHIFTED = int(ChamberMotif.DELIBERATIVE_SHIFT)


def _member(rep: int) -> Citizen:
    """One freshly-sortitioned member: chamber_position == issue_positions (== sincere_position),
    the exact state the Mode A loop fired on -- a distinct member each rep, not a literal replay,
    so temperature=0 determinism can't mask a real per-prompt difference."""
    c = Citizen(
        citizen_id=800 + rep,
        issue_positions=tuple((rep * 0.037 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
        sortition_seat_until_tick=16,
        sortition_terms_served=1,
    )
    c.chamber_position = c.issue_positions
    return c


def main() -> int:
    shipped = load_config()
    vllm_url = os.getenv("POLITY_VLLM_URL", "http://localhost:8000/v1")
    config = dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url=vllm_url))

    results: list[str] = []
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for rep in range(1, _REPS + 1):
            member = _member(rep)
            contexts = {member.citizen_id: ChamberContext(cid=member.citizen_id, ticks_left=12)}
            try:
                raw = client.complete_json(
                    system_prompt=build_chamber_system_prompt([member], config),
                    user_prompt=build_chamber_user_prompt([member], contexts),
                    json_schema=CHAMBER_JSON_SCHEMA,
                    max_tokens=compute_max_tokens(1) + _CHAMBER_THINK_TOKEN_ALLOWANCE,
                    think=True,
                )
                decision = decode_chamber_batch(raw, [member.citizen_id])[0]
                in_menu = decision.motif in (_SINCERE, _SHIFTED)
                print(f"  rep{rep}: OK motif={decision.motif} shifts={len(decision.shifts)} {'' if in_menu else '(OUT OF MENU)'}")
                results.append("ok" if in_menu else "out_of_menu")
            except LlmResponseError as exc:
                mode = "truncation" if "finish_reason='length'" in str(exc) else "other_response_error"
                print(f"  rep{rep}: FAILED ({mode}): {exc}")
                results.append(mode)
            except Exception as exc:  # noqa: BLE001 -- a failure IS the measurement here
                print(f"  rep{rep}: FAILED (transport): {exc}")
                results.append("transport_error")

    truncations = results.count("truncation")
    print("\n--- result ---")
    print(f"chamber_position == sincere_position, {_REPS} reps: {results}")
    print(f"truncations (Mode A signature): {truncations}/{_REPS} (Ollama post-fix: 0/7)")
    print("\n--- verdict ---")
    if truncations == 0:
        print("PASSES: the 2026-08-29 disambiguation fix still prevents the Mode A loop under vLLM/AWQ.")
    else:
        print(
            f"FAILS: {truncations}/{_REPS} truncated -- the disambiguation fix's effectiveness is "
            "model-specific and does not transfer to the AWQ-quantized weights unmodified."
        )
    return 0 if truncations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
