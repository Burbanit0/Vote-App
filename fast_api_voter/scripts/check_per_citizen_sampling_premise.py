"""
scripts/check_per_citizen_sampling_premise.py

Premise check for plan-llm-protocol-and-theory-program.md §3.A.1
("per-citizen deterministic sampling"), run BEFORE implementing it.

§3.A.1's argument: everything runs at temperature=0 (greedy argmax), and
"content-blind collapse is, mechanically, what greedy decoding does to a
weakly-discriminated distribution" -- so drawing each citizen's decision
from a per-citizen deterministic seed at temperature>0 should restore
population variance without giving up reproducibility.

That argument has a premise and an architectural problem, and both need
checking before any code ships.

**The architectural problem.** `seed` and `temperature` are per-REQUEST
body fields (llm_client.py), and pressure_action batches up to
llm.max_batch_size=25 citizens per request. A literal per-citizen seed
therefore requires chunk_size=1 -- 25x the call count, on the decision
type with the highest call volume in the project. The zero-cost
alternative is to sample OFFLINE from the logprobs §5.C already reads:
one greedy batched call gives P per citizen, then each citizen's outcome
is drawn with its own deterministic RNG. Same reproducibility, no extra
GPU work.

**The premise.** Offline sampling can only express signal that is already
in P. It cannot create any. So the question this script answers is:
on the SHIPPED model, does P(act=4) carry enough spread for sampling to
produce real population variance -- or is the distribution itself already
degenerate, in which case §3.A.1 changes nothing?

Reported per citizen and in aggregate:
  - greedy outcome (what production does today),
  - the outcome a per-citizen deterministic draw would give,
  - Bernoulli variance p(1-p), the ceiling on per-citizen variability,
  - the deterministic proxy's own expectation, as a reference point.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_per_citizen_sampling_premise.py
"""
from __future__ import annotations

import dataclasses
import hashlib
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
    build_pressure_user_prompt,
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
from api.domain.polity.simple_rules import deterministic_pressure_action  # noqa: E402

_TARGET_CID = 999
_BLANK_THRESHOLD = 0.5
_MANDATE_DEV = 0.1
_TICKS_TO_ELECTION = 10
_TICK = 7  # a fixed tick index, part of the per-citizen seed derivation
_SELF_GAPS = [
    0.02, 0.05, 0.08, 0.10, 0.15, 0.18,
    0.42, 0.47,
    0.53, 0.58,
    0.60, 0.80, 1.00, 1.30, 1.60, 1.90, 2.20,
]


def _vllm_config():
    shipped = load_config()
    model = os.environ.get("POLITY_PROBE_MODEL", shipped.llm.model)
    return dataclasses.replace(
        shipped,
        llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1", model=model),
    )


def _citizen_uniform(run_seed: int, citizen_id: int, tick: int, decision_type: str) -> float:
    """§3.A.1's own `(run_seed, citizen_id, tick, decision_type)` seed
    derivation, as a uniform draw in [0,1). blake2b rather than Python's
    hash(): hash() is randomized per process (PYTHONHASHSEED) and would
    silently destroy the exact reproducibility this whole design exists to
    preserve. Deterministic across processes, machines and Python
    versions."""
    key = f"{run_seed}|{citizen_id}|{tick}|{decision_type}".encode()
    digest = hashlib.blake2b(key, digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64


def _probe_citizen(cid: int, self_gap: float) -> tuple[Citizen, PressureContext]:
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


def main() -> int:
    config = _vllm_config()
    assert menu_acts(config.pressure_menu) == (0, 4)

    citizens, contexts, proxy = [], {}, {}
    for i, gap in enumerate(_SELF_GAPS):
        cid = 4000 + i
        citizen, context = _probe_citizen(cid, gap)
        citizens.append(citizen)
        contexts[cid] = context
        proxy[cid] = int(deterministic_pressure_action(citizen, gap, config.pressure_menu))

    print(f"per-citizen sampling premise check: model={config.llm.model} n={len(citizens)}")

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        content, tokens = client.complete_json_with_logprobs(
            system_prompt=build_pressure_system_prompt(citizens, config),
            user_prompt=build_pressure_user_prompt(citizens, contexts),
            json_schema=PRESSURE_JSON_SCHEMA, max_tokens=compute_max_tokens(len(citizens)),
            think=False, top_logprobs=10,
        )
    try:
        probes = locate_decision_field_logprobs(content, tokens, field="act")
    except LogprobAlignmentError as exc:
        print(f"ALIGNMENT FAILED: {exc}")
        return 1

    wait, nothing_ = int(PressureAct.WAIT_FOR_ELECTION), int(PressureAct.NOTHING)
    rows = []
    for probe in probes:
        gap = contexts[probe.cid].self_gap
        p = binary_probability(probe.token, true_value=str(wait), false_value=str(nothing_))
        greedy = wait if p > 0.5 else nothing_
        u = _citizen_uniform(config.run.seed, probe.cid, _TICK, "pressure_action")
        sampled = wait if u < p else nothing_
        rows.append((gap, probe.cid, p, greedy, sampled, proxy[probe.cid], p * (1 - p)))
    rows.sort()

    print(f"\n{'self_gap':>9}  {'P(act=4)':>10}  {'greedy':>7}  {'sampled':>8}  {'proxy':>6}  {'p(1-p)':>8}")
    for gap, _cid, p, greedy, sampled, prox, var in rows:
        print(f"{gap:>9.2f}  {p:>10.6f}  {greedy:>7}  {sampled:>8}  {prox:>6}  {var:>8.5f}")

    n = len(rows)
    greedy_wait = sum(1 for r in rows if r[3] == wait)
    sampled_wait = sum(1 for r in rows if r[4] == wait)
    proxy_wait = sum(1 for r in rows if r[5] == wait)
    mean_p = sum(r[2] for r in rows) / n
    mean_var = sum(r[6] for r in rows) / n

    print(f"\nact=4 rate — greedy (production today): {greedy_wait}/{n} = {greedy_wait/n:.1%}")
    print(f"act=4 rate — per-citizen deterministic draw: {sampled_wait}/{n} = {sampled_wait/n:.1%}")
    print(f"act=4 rate — deterministic proxy says:       {proxy_wait}/{n} = {proxy_wait/n:.1%}")
    print(f"\nmean P(act=4) = {mean_p:.6f}")
    print(f"mean Bernoulli variance p(1-p) = {mean_var:.6f}  "
          f"(max possible 0.25; this is the ceiling on per-citizen variability sampling can express)")
    expected_minority = sum(min(r[2], 1 - r[2]) for r in rows)
    print(f"expected minority-outcome count per {n} citizens = {expected_minority:.2f}")
    print("\nVERDICT: sampling can only express signal already present in P. "
          f"With mean p(1-p) = {mean_var:.6f}, a per-citizen draw changes "
          f"{expected_minority:.1f} of {n} decisions in expectation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
