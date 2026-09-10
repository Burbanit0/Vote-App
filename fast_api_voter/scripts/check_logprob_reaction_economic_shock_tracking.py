"""
scripts/check_logprob_reaction_economic_shock_tracking.py

plan-llm-protocol-and-theory-program.md §5.C, fourth application of the
logprob instrument -- but NOT a re-confirmation of reaction_to_event's
SCANDAL-branch collapse, which decide_reaction_to_event's own docstring
already marks RESOLVED on vLLM/AWQ (2026-09-06,
check_vllm_collapse_signatures_results.md): salience_delta varied
directionally-sensibly (0.20 vs 0.15) across the original two poles, no
collapse. Re-measuring an already-resolved branch would be low value.

The genuinely open gap that docstring names instead: "SCANDAL was chosen
specifically because it carries a real target ... ECONOMIC_SHOCK's target
is always null ... neither the original warning nor this resolution
should be assumed to transfer to that branch without its own check --
still untested, either backend." This probes exactly that: does
reaction_to_event's ECONOMIC_SHOCK branch track its own event-severity
signal (`magnitude` -- unique to this branch; SCANDAL has no analogue),
or is it flat regardless of how severe the shock is?

`magnitude` is a CALL-level fact (build_reaction_user_prompt takes one
float for the whole call, unlike per-citizen ctx.event_salience), so this
runs one call per magnitude point, each batching 3 citizens together
(matching the original diagnostic's own "3 different citizens each"
precedent) with event_salience fixed at 0.0 (untouched -- isolates
magnitude's own effect, the SCANDAL branch already established prior
salience's own effect separately). Magnitude spans 0.05 (barely
noticeable) to 1.5 (well past events.economy_shock_threshold=0.5, "major"
per the shipped config), crossing that threshold partway through. Reads
P(motif=402, ECONOMIC_SHOCK_REACTION) vs P(motif=403, EVENT_PERSONALLY_
IRRELEVANT) via binary_probability -- the two only legal motifs for this
event_type. Real production shape throughout: build_reaction_system_
prompt/build_reaction_user_prompt, REACTION_JSON_SCHEMA, think=False
(this decision type's own production value).

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_logprob_reaction_economic_shock_tracking.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.codebook import EventType  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ReactionContext,
    build_reaction_system_prompt,
    build_reaction_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    binary_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import REACTION_JSON_SCHEMA  # noqa: E402

_MAGNITUDES = [0.05, 0.40, 0.75, 1.10, 1.50]  # crosses economy_shock_threshold=0.5 partway through
_REACTORS_PER_CALL = 3  # matches the original diagnostic's own "3 different citizens each"


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _reactor(cid: int) -> Citizen:
    citizen = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.013 + d * 0.017) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
    )
    citizen.event_salience = 0.0  # untouched by any past event -- isolates magnitude's own effect
    return citizen


def main() -> int:
    config = _vllm_config()
    print(f"reaction_to_event/ECONOMIC_SHOCK magnitude probe: {len(_MAGNITUDES)} magnitudes "
          f"{_MAGNITUDES}, {_REACTORS_PER_CALL} reactors per call, event_salience=0.0 (fixed)")

    rows = []
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for i, magnitude in enumerate(_MAGNITUDES):
            reactors = [_reactor(7000 + i * 10 + j) for j in range(_REACTORS_PER_CALL)]
            contexts = {r.citizen_id: ReactionContext(cid=r.citizen_id, event_salience=0.0) for r in reactors}
            system_prompt = build_reaction_system_prompt(reactors, EventType.ECONOMIC_SHOCK, config)
            user_prompt = build_reaction_user_prompt(
                reactors, contexts, event_type=EventType.ECONOMIC_SHOCK, target=None, magnitude=magnitude,
            )
            content, tokens = client.complete_json_with_logprobs(
                system_prompt=system_prompt, user_prompt=user_prompt,
                json_schema=REACTION_JSON_SCHEMA, max_tokens=compute_max_tokens(len(reactors)),
                think=False,  # decide_reaction_to_event's own production value
                top_logprobs=10,
            )
            try:
                # value_char_offset=2: ReactionMotif's legal values here
                # (402/403) share the leading "40" -- see that parameter's
                # own docstring for why offset=0 would be uninformative.
                probes = locate_decision_field_logprobs(content, tokens, field="motif", value_char_offset=2)
            except LogprobAlignmentError as exc:
                print(f"  ALIGNMENT FAILED at magnitude={magnitude}: {exc}")
                continue
            for probe in probes:
                # value_char_offset=2 locates the digit that actually
                # discriminates 402 from 403 (both share the leading "40"),
                # so the token's own alternatives are keyed by "2"/"3", not
                # the full 3-digit strings -- confirmed live: the located
                # token's own text is a bare single digit.
                p_react = binary_probability(probe.token, true_value="2", false_value="3")
                rows.append((magnitude, probe.cid, p_react, probe.token.token))

    print(f"\n{'magnitude':>9}  {'cid':>5}  {'P(motif=402)':>12}  {'chosen_motif':>13}")
    for magnitude, cid, p_react, chosen in rows:
        major = "  (major)" if magnitude > 0.5 else ""
        print(f"{magnitude:>9.2f}  {cid:>5}  {p_react:>12.6f}  {chosen:>13}{major}")

    print(f"\naligned decisions: {len(rows)}/{len(_MAGNITUDES) * _REACTORS_PER_CALL}")
    by_magnitude: dict[float, list[float]] = {}
    for magnitude, _cid, p_react, _chosen in rows:
        by_magnitude.setdefault(magnitude, []).append(p_react)
    means = {m: sum(ps) / len(ps) for m, ps in by_magnitude.items()}
    for m in sorted(means):
        print(f"mean P(motif=402) at magnitude={m:.2f}: {means[m]:.6f}")
    if len(means) >= 2:
        values = [means[m] for m in sorted(means)]
        print(f"\nfull spread across all {len(values)} magnitude points: {max(values) - min(values):.6f} "
              f"(min={min(values):.6f}, max={max(values):.6f})")
        lowest, highest = means[min(means)], means[max(means)]
        print(f"lowest-to-highest magnitude difference: {highest - lowest:+.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
