"""
scripts/check_pressure_gap_tracking_geometry_b.py

Replication of check_logprob_pressure_action_gap_tracking.py under a
DIFFERENT probe geometry — the one loose end left by §2's base-vs-instruct
result (check_base_vs_instruct_results.md): the base arm's +0.089
separation / r=+0.378 on pressure_action was the sole evidence supporting
§2's alignment hypothesis, and at n=17 it is not significant (p≈0.134).

Why geometry and not seeds: `llm.temperature` is pinned to 0.0, and at
temperature=0 sampling is argmax — VllmJsonClient's own docstring records
that the seed "does nothing about §15bis.4c's batch-composition
nondeterminism, which is a kernel floating-point reduction order property,
not a sampling one". A different seed reproduces byte-identical output and
confirms nothing. What an underpowered n=17 reading CAN be an artifact of
is the incidental construction choices, so those are what this varies:

  - different cid block (9000+ rather than 4000+), which is the only
    per-citizen field other than self_gap that reaches this prompt;
  - different self_gap values — same 0.02..2.20 span, but 17 points placed
    differently (no value shared with geometry A except the endpoints,
    which are kept so the poles remain comparable);
  - reversed batch order (descending self_gap), so any position-within-
    chunk effect works against the original result rather than with it;
  - a different fixed mandate_dev (0.25 rather than 0.10) — still constant
    across citizens, so self_gap is still the only varying signal, but the
    call-level constant is no longer the same one.

Everything else is held identical to geometry A: same prompts, same
schema, same think=False, same closed shipped menu, same instrument
(locate_decision_field_logprobs + binary_probability), same statistics.

Run against BOTH arms to be meaningful:
    POLITY_PROBE_MODEL=qwen3:4b      python .../check_pressure_gap_tracking_geometry_b.py
    POLITY_PROBE_MODEL=qwen3:4b-base python .../check_pressure_gap_tracking_geometry_b.py
"""
from __future__ import annotations

import dataclasses
import math
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

_TARGET_CID = 777          # geometry A used 999
_BLANK_THRESHOLD = 0.5     # unchanged: it is the decision boundary under test
_MANDATE_DEV = 0.25        # geometry A used 0.10
_TICKS_TO_ELECTION = 6     # geometry A used 10
_CID_BASE = 9000           # geometry A used 4000

# Same span and same 8-below / 9-above split as geometry A (so the
# separation statistic stays comparable), but different interior values.
_SELF_GAPS = [
    0.02, 0.07, 0.12, 0.21, 0.28, 0.34,       # clearly satisfied
    0.44, 0.49,                                # boundary, below
    0.55, 0.62,                                # boundary, above
    0.70, 0.90, 1.15, 1.45, 1.75, 2.00, 2.20,  # clearly discontented
]


def _vllm_config():
    shipped = load_config()
    model = os.environ.get("POLITY_PROBE_MODEL", shipped.llm.model)
    return dataclasses.replace(
        shipped,
        llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1", model=model),
    )


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


def _pearson(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """(r, two-tailed p). Same statistic check_base_vs_instruct_results.md
    reports, computed here so the replication reports it directly rather
    than being read off by hand afterwards."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return 0.0, 1.0
    r = cov / math.sqrt(vx * vy)
    if abs(r) >= 1.0:
        return r, 0.0
    t = r * math.sqrt(n - 2) / math.sqrt(1 - r * r)
    # two-tailed p from the t distribution via the regularized incomplete beta
    df = n - 2
    x = df / (df + t * t)
    a, b = df / 2, 0.5

    def betacf(a: float, b: float, x: float) -> float:
        maxit, eps, fpmin = 200, 3e-16, 1e-300
        qab, qap, qam = a + b, a + 1, a - 1
        c, d = 1.0, 1 - qab * x / qap
        d = fpmin if abs(d) < fpmin else d
        d = 1 / d
        h = d
        for m in range(1, maxit + 1):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1 + aa * d
            c = 1 + aa / c
            d, c = (fpmin if abs(d) < fpmin else d), (fpmin if abs(c) < fpmin else c)
            d = 1 / d
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1 + aa * d
            c = 1 + aa / c
            d, c = (fpmin if abs(d) < fpmin else d), (fpmin if abs(c) < fpmin else c)
            d = 1 / d
            de = d * c
            h *= de
            if abs(de - 1) < eps:
                break
        return h

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    if x < (a + 1) / (a + b + 2):
        p = math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta) * betacf(a, b, x) / a
    else:
        p = 1 - math.exp(b * math.log(1 - x) + a * math.log(x) - lbeta) * betacf(b, a, 1 - x) / b
    return r, p


def main() -> int:
    config = _vllm_config()
    assert menu_acts(config.pressure_menu) == (0, 4)

    # Descending self_gap: geometry A batched ascending, so any
    # position-within-chunk effect now works against A's result.
    gaps = sorted(_SELF_GAPS, reverse=True)
    citizens, contexts = [], {}
    for i, gap in enumerate(gaps):
        cid = _CID_BASE + i
        citizen, context = _probe_citizen(cid, gap)
        citizens.append(citizen)
        contexts[cid] = context
    expected = [c.citizen_id for c in citizens]

    print(f"geometry B: model={config.llm.model} n={len(citizens)} cids={_CID_BASE}+ "
          f"target={_TARGET_CID} mandate_dev={_MANDATE_DEV} ticks={_TICKS_TO_ELECTION} order=descending")

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

    rows = []
    for probe in probes:
        gap = contexts[probe.cid].self_gap
        p_wait = binary_probability(
            probe.token,
            true_value=str(int(PressureAct.WAIT_FOR_ELECTION)), false_value=str(int(PressureAct.NOTHING)),
        )
        rows.append((gap, p_wait, probe.token.token))
    rows.sort()

    print(f"\n{'self_gap':>9}  {'P(act=4)':>10}  {'chosen':>7}")
    for gap, p, chosen in rows:
        print(f"{gap:>9.2f}  {p:>10.6f}  {chosen:>7}")

    below = [p for g, p, _ in rows if g < _BLANK_THRESHOLD]
    above = [p for g, p, _ in rows if g >= _BLANK_THRESHOLD]
    sep = sum(above) / len(above) - sum(below) / len(below)
    r, p_value = _pearson([g for g, _, _ in rows], [p for _, p, _ in rows])
    print(f"\naligned: {len(rows)}/{len(citizens)} (decoded cids match expected: {sorted(p.cid for p in probes) == sorted(expected)})")
    print(f"mean P(act=4) below={sum(below)/len(below):.6f} (n={len(below)}) "
          f"above={sum(above)/len(above):.6f} (n={len(above)})")
    print(f"separation = {sep:+.6f}   (geometry A, base arm: +0.089183)")
    print(f"pearson r  = {r:+.4f}  two-tailed p = {p_value:.4f}   (geometry A, base arm: +0.3781, p=0.1345)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
