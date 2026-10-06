"""
scripts/check_pressure_batch_order_randomized.py

Properly randomized version of check_pressure_batch_size_sweep.py, written
after that script's first conclusion turned out to be an artifact of its
own construction.

What happened, recorded because it matters more than the result. The sweep
built each batch by ALTERNATING clearly-below / clearly-above threshold
values. Under that construction the model looked catastrophic: 1/1 at
batch 1 then at-or-below the 50% blind-guess baseline at every larger size,
including 0/12 with separation -0.9157 (confidently inverted). The obvious
reading was "per-record attention collapses at batch 2".

A control in the same script re-ran every size with the order permuted.
The picture inverted: 2/2, 8/8, 12/12, 17/17 and 24/25 -- near-perfect at
exactly the sizes that had just "collapsed". The model had been
pattern-completing on the alternation rather than reading values, and the
0/12 inversion was that completion landing one position out of phase.

So the first result measured the input's regularity, not the model's batch
capacity. That control is the only reason a confident and wrong conclusion
did not get written up.

This script fixes the design properly. Its predecessor's "shuffle" was a
single fixed permutation that, at small n, barely disturbs the alternation
(at n=3 it is simply a reversal, which preserves it). Here each batch size
is run under SEVERAL genuinely random orders, with per-order results
reported rather than a single number, so order-sensitivity is visible
instead of hidden. Values are drawn from a wide pool and shuffled
independently per trial.

Determinism is preserved the way this project requires: the RNG is seeded
from `(run_seed, batch_size, trial)`, so the whole sweep replays identically.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_pressure_batch_order_randomized.py
"""
from __future__ import annotations

import dataclasses
import json
import os
import random
import statistics
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
_BATCH_SIZES = [1, 3, 5, 8, 12, 17, 25]
_TRIALS = 3

# Clearly on one side or the other -- this sweep asks whether per-record
# values are read at all, not about precision near the cut.
_BELOW = [0.02, 0.04, 0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30]
_ABOVE = [0.80, 0.90, 0.95, 1.00, 1.15, 1.30, 1.45, 1.60, 1.75, 1.90, 2.00, 2.10, 2.20]


def _vllm_config():
    shipped = load_config()
    model = os.environ.get("POLITY_PROBE_MODEL", shipped.llm.model)
    return dataclasses.replace(
        shipped,
        llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1", model=model),
    )


def _gaps(n: int, rng: random.Random) -> list[float]:
    """n values, half from each side (so a constant answer scores ~50%),
    in independently random order."""
    half = n // 2
    picked = rng.sample(_BELOW, half) + rng.sample(_ABOVE, n - half)
    rng.shuffle(picked)
    return picked


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
    """The rule stated outright -- deliberately not shippable (it makes the
    LLM a slow reimplementation of a two-line function), used here so that
    any failure is attributable to batch construction and nothing else."""
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

    print(f"randomized batch-order sweep: model={config.llm.model}  rule STATED, threshold SUPPLIED  "
          f"{_TRIALS} random orders per size  (shipped chunk size = {config.llm.max_batch_size})")
    print(f"\n{'batch':>6}  {'per-trial accuracy':>22}  {'mean':>6}  {'verdict':>10}")

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for n in _BATCH_SIZES:
            rates = []
            for trial in range(_TRIALS):
                rng = random.Random(f"{config.run.seed}|{n}|{trial}")
                gaps = _gaps(n, rng)
                citizens, contexts = [], {}
                for i, gap in enumerate(gaps):
                    c, ctx = _probe(6000 + n * 100 + trial * 30 + i, gap)
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
                    print(f"{n:>6}  trial {trial}: ALIGNMENT FAILED: {exc}")
                    continue
                correct = 0
                for pr in probes:
                    g = contexts[pr.cid].self_gap
                    p = binary_probability(pr.token, true_value=str(wait), false_value=str(nothing_))
                    if (wait if p > 0.5 else nothing_) == (wait if g > _BLANK_THRESHOLD else nothing_):
                        correct += 1
                rates.append(correct / len(probes))
            if not rates:
                continue
            mean = statistics.fmean(rates)
            verdict = "clean" if min(rates) >= 0.95 else ("variable" if max(rates) >= 0.95 else "poor")
            cells = "  ".join(f"{r:>5.0%}" for r in rates)
            print(f"{n:>6}  {cells:>22}  {mean:>5.0%}  {verdict:>10}")

    print("\nA constant answer scores ~50% by construction. 'variable' means at least one order "
          "was near-perfect and at least one was not -- i.e. the batch's own composition, not its "
          "size alone, drives the outcome.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
