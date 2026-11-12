# Phase 4 (schema-embedded reasoning field) — result: FAILS on the informative subset

Run 2026-09-05, `check_pressure_action_reasoning_field_first.py`, against
`plan-pressure-action-resolution.md`'s own Phase 4 and
`plan-pressure-action-remediation.md`'s §3.4. Pre-registered before this run
(this document's own git history shows the criterion — ≥80% agreement,
checked separately per class — committed before the live call, not adjusted
after seeing results).

## What blocked the original 2026-08-30 attempt, now actually fixed

`llm_client.py`'s `json.dumps(body, sort_keys=True, ...)` alphabetizes the
entire request body, including the JSON schema sent in `format` — regardless
of Pydantic field declaration order. The 2026-08-30 qualitative check
confirmed directly on raw generated JSON that `act` was emitted **before**
`reasoning`, the exact opposite of what that test meant to exercise. That
plan doc explicitly forecloses touching `sort_keys` itself for this
remediation alone (it protects byte-for-byte request reproducibility for
every decision type in the project — reopening it needs its own separate
scoping, never a local workaround here).

Fix, scoped to this standalone test schema only (the real `PressureDecision`
is untouched): the field is renamed `a_reasoning` — `'a_reasoning' < 'act' <
'cid' < 'motif'` alphabetically, verified directly against the exact request
body `llm_client.py` builds (`sort_keys=True` output inspected before any
live call). This is the option `plan-pressure-action-resolution.md` §4
itself flagged as "by far the least costly" of three named, and the only one
that doesn't touch code shared by every decision type.

**Mechanism confirmed live, not assumed**: every one of 70 calls had
`a_reasoning` appear before `act` in the raw response JSON (checked via
direct string search on the stripped response, the same discipline that
caught the original bug) — 70/70 order-confirmed, 0 violations. Unlike
2026-08-30's attempt, this run genuinely exercised what it meant to test.

## The pooled number is a base-rate artifact — do not trust it alone

| | agreement | note |
|---|---|---|
| Pooled (all 70) | 57/70 (81.4%) | clears the pre-registered ≥80% bar |
| should-act (ratio>1.5, n=17) | 4/17 (23.5%) | the only informative subset |
| should-not-act (ratio<0.5, n=53) | 53/53 (100.0%) | trivially satisfied by defaulting to inaction |

This is the exact trap `plan-pressure-action-resolution.md` §2.3 already
named once in this same investigation ("the apparent 75.7% pass was a
base-rate artifact from class imbalance"). The 70-citizen harness is
dominated 53/70 by the should-not-act majority; a model that defaults to
inaction near-universally clears the pooled bar without demonstrating
anything about the actual collapse under test. **Every one of the 13
disagreements is a false negative** (expected=act, got=NOTHING or
WAIT_FOR_ELECTION) — zero false positives in either direction.

Ratio alone does not cleanly separate the 4 agreeing should-act cases from
the 13 disagreeing ones: cid=74 (ratio=7.39, the single most clear-cut
should-act case in the entire dataset) still disagreed, while cid=45
(ratio=1.80, one of the weakest should-act signals) agreed. Whatever
resolves individual cases correctly, it is not simply "how far past the
1.5 threshold."

## Verdict: the third pre-registered outcome, not the first

`plan-pressure-action-remediation.md` §3.4 named three possible readings in
advance:
1. ≥80% (on the actual criterion, not a pooled artifact) — the mechanism is
   real and actionable.
2. Reasoning itself content-blind — same failure as §3.2, confirmed under
   grammar-constrained decoding too.
3. Reasoning varies plausibly but act/motif still collapse — a NEW, distinct
   signature: a reasoning-to-decision translation problem, not a
   content-blindness one.

This run lands on **(3)**. 70 distinct reasoning strings (not content-blind,
rules out (2)), each grounded in the citizen's own `self_gap`/`mandate_dev`
values in the generated text — but the collapse toward inaction survives
correctly-ordered, genuinely-varying reasoning. The schema-embedded
mechanism from §3.4 is confirmed real (order verified, not assumed) and
confirmed **insufficient** on its own.

## Where this leaves the investigation

Phase 2 (`plan-pressure-action-resolution.md`) already returned all-negative
across three isolated variables (temperature 0.7, grammar-constraint
removal, few-shot examples). Phase 4 was the one remaining identified
lever, explicitly gated behind its own scoping decision because it touches
`sort_keys`-adjacent territory. With Phase 4 now also negative — for a
different, more specific reason than Phase 2's paths (a translation
problem, not decoding or sampling) — **every path this investigation has
identified is exhausted**. `pressure_action`'s four confirmed act/response
collapses remain marked unreliable in production (the `RELIABILITY WARNING`
in `llm_behavior_engine.py`), unchanged by this result. No new lever is
proposed here; identifying one would be a fresh investigation, not a
continuation of this one's existing scope.
