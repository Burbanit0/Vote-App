"""
scripts/check_pressure_batch_size_sweep.py

Locates the batch size at which pressure_action stops reading per-citizen
data, using a task the model is PROVEN able to do at size 1.

Why this is the right experiment. check_pressure_missing_threshold.py found
that with the decision rule fully stated in the prompt and both numbers
supplied (`self_gap`, `blank_threshold`):

  - at batch size 1  -> separation **+0.993**, both citizens decided exactly
    as the stated rule requires;
  - at batch size 17 -> separation **+0.0001**, all 17 citizens identical,
    including ones the stated rule unambiguously puts on the other side.

Same prompt, same rule, same model. So the failure is not reasoning,
framing, or alignment -- it is what happens to per-record attention as a
batch grows. This sweep finds where.

This is not a new phenomenon in this codebase, which is what makes it
actionable: `cast_votes`'s own docstring records the same thing for
vote_cast -- "batching multiple voters into one call makes the model stop
actually reading each voter's own `distances` field at all", 100% correct
at batch 1 and 3, "0-2/5 at 5", "a near-uniform identity-permutation
collapse at the shipped chunk size of 25". vote_cast responded by cutting
its chunk size to 1 (later 3 on vLLM, re-verified). **pressure_action was
never re-tested and still runs at llm.max_batch_size = 25** -- it has no
ground truth of its own, so nothing forced the check.

The prompt used here states the rule outright, which is deliberately NOT a
shippable prompt (it would make the LLM a slow reimplementation of a
two-line function). It is used because it removes every other explanation:
any failure is then purely a function of how many citizens share the call.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_pressure_batch_size_sweep.py
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.codebook import PressureAct  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    binary_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

_TARGET_CID = 999
_BLANK_THRESHOLD = 0.5
_MANDATE_DEV = 0.1
_TICKS_TO_ELECTION = 10
_BATCH_SIZES = [1, 2, 3, 5, 8, 12, 17, 25]  # 25 = the shipped llm.max_batch_size


def _vllm_config():
    shipped = load_config()
    model = os.environ.get("POLITY_PROBE_MODEL", shipped.llm.model)
    return dataclasses.replace(
        shipped,
        llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1", model=model),
    )


def _gaps_shuffled(n: int) -> list[float]:
    """Same values as _gaps_for, in a deterministic pseudo-random order.

    Why this control exists: _gaps_for ALTERNATES below/above, and an
    alternating input invites pattern completion -- a model emitting a
    plausible alternating sequence without reading any value would score
    ~50%, or 0% if offset by one. The batch-12 result (0/12, separation
    -0.9157, i.e. confidently inverted) looks exactly like that. If the
    failure is real it must survive removing the pattern; if accuracy jumps
    here, the alternation was an artifact of my own construction."""
    gaps = _gaps_for(n)
    # A fixed permutation, deterministic across runs -- no RNG seeding needed.
    order = sorted(range(n), key=lambda i: ((i * 7919 + 104729) % 10007))
    return [gaps[i] for i in order]


def _gaps_for(n: int) -> list[float]:
    """n self_gap values alternating clearly-below / clearly-above the
    threshold, so every batch size faces the same discrimination task and
    a constant answer can never score better than ~50%. Deliberately avoids
    near-boundary values: this sweep is about whether per-record data is
    read at all, not about precision near the cut."""
    below = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.02, 0.08, 0.12, 0.18, 0.22, 0.28, 0.04]
    above = [2.20, 1.90, 1.60, 1.30, 1.00, 0.90, 2.00, 1.75, 1.45, 1.15, 0.95, 0.80, 2.10]
    out = []
    for i in range(n):
        out.append(below[i // 2] if i % 2 == 0 else above[i // 2])
    return out


def _probe(cid: int, self_gap: float) -> tuple[Citizen, PressureContext]:
    citizen = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.017 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=_BLANK_THRESHOLD,
        ambition_score=0.5,
    )
    context = PressureContext(
        cid=cid, target=_TARGET_CID, self_gap=self_gap, mandate_dev=_MANDATE_DEV,
        ticks_to_election=_TICKS_TO_ELECTION, available=(0, 4),
        petition_open=False, petition_expires_at_tick=None, already_signed=False, neighbors_acting=None,
    )
    return citizen, context


def _user_prompt(consulted, contexts) -> str:
    blocks = []
    for c in consulted:
        ctx = contexts[c.citizen_id]
        payload = ctx.to_payload()
        payload["blank_threshold"] = round(c.blank_threshold, 4)
        blocks.append({
            "cid": c.citizen_id, "target": ctx.target, "ctx": payload,
            "available": list(ctx.available),
            "petition": {"open": ctx.petition_open, "expires_at_tick": ctx.petition_expires_at_tick,
                         "already_signed": ctx.already_signed},
        })
    return json.dumps({"consulted": blocks}, sort_keys=True, separators=(",", ":"))


def _system_prompt(consulted, config) -> str:
    base = build_pressure_system_prompt(consulted, config)
    rule = (
        "ctx.blank_threshold : le seuil d'acceptabilite PROPRE a ce citoyen, "
        "sur la meme echelle que ctx.self_gap. REGLE : si self_gap est "
        "STRICTEMENT SUPERIEUR a blank_threshold, ce citoyen agit et tu "
        "reponds act=4 (attendre la prochaine election) ; si self_gap est "
        "INFERIEUR OU EGAL a blank_threshold, ce citoyen est satisfait et tu "
        "reponds act=0 (ne rien faire).\n"
    )
    return base.replace("IMPORTANT : la liste decisions", rule + "IMPORTANT : la liste decisions", 1)


def main() -> int:
    config = _vllm_config()
    assert menu_acts(config.pressure_menu) == (0, 4)
    wait, nothing_ = int(PressureAct.WAIT_FOR_ELECTION), int(PressureAct.NOTHING)

    print(f"pressure_action batch-size sweep: model={config.llm.model}  "
          f"rule STATED in prompt, threshold SUPPLIED  (shipped chunk size = {config.llm.max_batch_size})")
    print(f"\n{'batch':>6}  {'correct':>9}  {'rate':>7}  {'separation':>11}  {'mean p(1-p)':>12}  {'verdict':>10}")

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
      for ordering, gapfn in (("alternating", _gaps_for), ("shuffled", _gaps_shuffled)):
        print(f"\n-- ordering: {ordering} --")
        for n in _BATCH_SIZES:
            gaps = gapfn(n)
            citizens, contexts = [], {}
            for i, gap in enumerate(gaps):
                c, ctx = _probe(5000 + n * 100 + i + (0 if ordering == "alternating" else 50), gap)
                citizens.append(c)
                contexts[c.citizen_id] = ctx
            content, tokens = client.complete_json_with_logprobs(
                system_prompt=_system_prompt(citizens, config),
                user_prompt=_user_prompt(citizens, contexts),
                json_schema=PRESSURE_JSON_SCHEMA, max_tokens=compute_max_tokens(n),
                think=False, top_logprobs=10,
            )
            try:
                probes = locate_decision_field_logprobs(content, tokens, field="act")
            except LogprobAlignmentError as exc:
                print(f"{n:>6}  ALIGNMENT FAILED: {exc}")
                continue
            rows = [(contexts[pr.cid].self_gap,
                     binary_probability(pr.token, true_value=str(wait), false_value=str(nothing_)))
                    for pr in probes]
            correct = sum(1 for g, p in rows
                          if (wait if p > 0.5 else nothing_) == (wait if g > _BLANK_THRESHOLD else nothing_))
            below = [p for g, p in rows if g <= _BLANK_THRESHOLD]
            above = [p for g, p in rows if g > _BLANK_THRESHOLD]
            sep = (sum(above) / len(above) - sum(below) / len(below)) if below and above else float("nan")
            mv = sum(p * (1 - p) for _g, p in rows) / len(rows)
            rate = correct / len(rows)
            verdict = "clean" if rate == 1.0 else ("degraded" if rate >= 0.7 else "COLLAPSED")
            print(f"{n:>6}  {correct:>4}/{len(rows):<4}  {rate:>6.0%}  {sep:>+11.4f}  {mv:>12.5f}  {verdict:>10}")

    print("\nA constant answer scores ~50% here by construction (the batch alternates below/above "
          "the threshold), so 'COLLAPSED' means the model is at or below what answering blindly gives.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
