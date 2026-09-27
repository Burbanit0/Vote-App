# `recycle_after_n_calls` vs. `_VOTE_CAST_MAX_CHUNK_SIZE=1` — a calibration tension, documented before testing

Written 2026-08-21, GPU, immediately after the v6b Lot 4 acceptance run (with today's chunk-size fix
already applied) crashed on a new, previously-unseen failure mode. Per explicit instruction: this
tension is documented in writing *before* any empirical test is run against it, so the hypothesis and
its reasoning are on record independent of whatever the test finds — the same discipline the
`llm_test_harness` itself enforces structurally (pre-registration, no post-hoc rewrite).

## What just happened

The relaunched acceptance run (all of today's earlier fixes applied, including
`_VOTE_CAST_MAX_CHUNK_SIZE` 3→1) crashed on citizen 10's own `cast_votes` call: attempt 1 truncated
(`finish_reason='length'`), and both replay attempts (deterministic at temp=0) produced the exact
same internally-inconsistent decision — `blank=1` together with a full, non-empty `ranking`,
violating `VoteCastDecision`'s own hard rule (§3.6.1). This is **not** a defensible edge case: citizen
10 is themself one of the run's 5 candidates, their own distance-to-self is 0.087 against a
blank_threshold of 0.565, and every candidate in the field is within threshold — the correct answer
is unambiguously `blank=0`, ranked with themself first. The model's output is simply wrong, and wrong
in a way JSON-schema-level structured decoding cannot prevent, because `blank`/`ranking` coherence is
a cross-field semantic rule, not a structural one — exactly the category of risk this project has
already named repeatedly for other decision types (`ResponseDecision`'s stance/motif rule,
`PressureDecision`'s deliberately-unenforced act/motif pairing) but had never actually seen fire for
`vote_cast` until now.

## The tension, stated before testing

This run's own config sets `llm.recycle_after_n_calls = 6` — not the shipped default (`null`,
disabled), but a value chosen specifically for this acceptance run per bug 4's own mitigation
(`llm_batching_determinism_results_gpu.md`, deployed in commit `49e3631`). That mitigation's own
measured capacity (~8 distinct prompts before the cache pool enters its degeneration zone, 0/24
failures below 7 cached prompts vs. 40-50% at 7-8) was measured against **one specific prompt
shape**: `campaign_positioning`, `think=True`, a large token budget. The mitigation doc says this
explicitly, in its own "honesty about what remains unresolved" section:

> Le seuil mesuré (~8 prompts, capacité de risque à partir de 7) l'est pour UN prompt shape précis
> (`campaign_positioning`, `think=True`, grand budget de tokens) sur LA mémoire de CE conteneur — pas
> prouvé général à tout mélange de types de décision. `recycle_after_n_calls` reste `null` par défaut
> pour cette raison.

`cast_votes` at `_VOTE_CAST_MAX_CHUNK_SIZE=1` is a **structurally different prompt shape** from the
one that calibration was measured against: each call now covers exactly one voter (≈1600-1700
prompt tokens per the live docker logs, `task.n_tokens = 1598`), not `campaign_positioning`'s own
larger multi-nominee batch. And today's own chunk-size fix independently **tripled** the total call
volume for `cast_votes` across a run (96 → 285 calls over 3 elections, per this session's own earlier
estimate) — meaning far more, smaller, more numerous distinct prompts now pass through the cache pool
per unit of simulated work than the mitigation's own calibration run ever exercised.

**The hypothesis, stated plainly**: `recycle_after_n_calls=6` was calibrated as "prudently below the
measured threshold" for a *different, larger* prompt shape. Whether 6 calls of `cast_votes`-shaped
single-voter prompts is *also* safely below whatever this shape's own degeneration threshold is has
never been measured — bug 4's own doc flags exactly this generalization gap as unresolved, and this
crash is the first time it has actually been exercised at chunk_size=1's scale. If the degeneration
threshold scales with something like distinct-prompt *volume* or *diversity* rather than raw
`complete_json` call count, then a smaller, more numerous prompt shape could plausibly reach the same
danger zone in *fewer* calls than 6 — meaning `recycle_after_n_calls=6` would no longer be "prudently
below" anything for this shape, it would just be an unvalidated number carried over from a different
experiment.

## Why "just tighten the number" would not actually close this, even if the test confirms it

If the empirical test below confirms cast_votes-at-chunk_size=1 degenerates within (or close to) the
current 6-call window, the *tempting* fix is to pick a smaller constant — 3, say — and move on. That
would repeat exactly the mistake this document exists to avoid: `recycle_after_n_calls` is currently
a flat call-count threshold, blind to what kind of call it's counting. The next time chunk size
changes for *any* decision type (or population scales up at the already-anticipated v3 milestone,
1000 citizens instead of 100 — which changes chunk counts for population-wide decision types like
`cast_votes`/`candidacy_considered`/`reaction_to_event` directly), the same mismatch reappears,
silently, until it crashes another run. A durable fix has to make the threshold a function of the
actual prompt volume/shape being pushed through the client — not a single global constant recalibrated
by hand after every scale change. What that should concretely look like is scoped *after* the test
below, not guessed at here.

## Test protocol (registered via `llm_test_harness` before running, not adjusted after seeing results)

Three pre-registered experiments (harness IDs below), each 30 real single-voter `cast_votes` calls
against the same real 30 voters (citizens 0-29) and the same real 5 candidates (81, 10, 15, 88, 24,
with the crashed run's own actual `campaign_positioning` shifts applied) — `A_none`
(`recycle_after_n_calls=None`), `B_six` (`=6`, the crashed run's own production setting), `C_three`
(`=3`, tightened). Full protocol/hypotheses/decision criteria in
`C:\Users\burba\AppData\Local\Temp\claude\...\scratchpad\cache_recycle_tension_experiment.py`
(script content, not repo-tracked — this doc's own quoted criteria below are copied from it verbatim).

## Results (2026-08-22, GPU, real qwen3:8b)

| Condition | `recycle_after_n_calls` | failures | failure_rate | failing trial (cid) |
|---|---|---|---|---|
| `A_none` (`20260821T235923Z-7f48309e`) | `None` (disabled) | 2/30 | 0.067 | #8 (cid=7), #20 (cid=19) |
| `B_six` (`20260822T000438Z-7ab5ed1b`) | `6` (production) | 2/30 | 0.067 | #8 (cid=7), #29 (cid=28) |
| `C_three` (`20260822T001051Z-26d9cf27`) | `3` (tightened) | 2/30 | 0.067 | #8 (cid=7), #29 (cid=28) |

Every single one of the 6 failures across all 90 trials was the **identical error type** —
`blank=1 requires an empty ranking (§3.6.1 hard rule)` schema-coherence violation. **Zero**
`finish_reason='length'` truncations in any of the 90 trials, in any condition.

**The hypothesis is REJECTED, not confirmed, per the pre-registered criteria themselves**:

- **Condition A's own criterion** ("first failure at or before position 6 confirms the tension...
  strictly after position 7, or no failure at all, would suggest this shape is not more fragile than
  campaign_positioning's own calibration"): first failure at **position 8** — strictly after 7. Does
  not confirm the tension.
- **Condition C vs B's own criterion** ("failure_rate == failure_rate in condition B... would suggest
  the recycle threshold is not the operative variable and a different mechanism is at play"):
  failure_rate is **identical** between B and C (0.067 both) — this is exactly the named
  not-the-operative-variable outcome.
- **The strongest single piece of evidence**: **cid=7 fails at trial position #8 in all three
  conditions, identically** — and B/C additionally share their *second* failure at cid=28/#29,
  identically. If cache-pool degeneration (a function of `recycle_after_n_calls`) were driving this,
  changing the recycle setting should have shifted *which* calls land in a degraded cache state.
  It didn't move at all between recycle=6 and recycle=3, and recycle=disabled-entirely (`A_none`,
  never preemptively reloads) produced the same rate too.

**Conclusion**: `recycle_after_n_calls` is not the operative variable for this failure.
`blank=1`+non-empty-`ranking` is a **deterministic, per-voter-prompt** defect at temperature=0 —
reproducible regardless of cache-recycling state, i.e. a genuine `cast_votes` *model-reliability*
bug, unrelated to bug 4's cache-degeneration/truncation mechanism this document's own tension
hypothesis was built around. This also explains why the crashed run's own 2 replay attempts (same
`recycle_after_n_calls=6` setting, same prompt) failed identically both times: retrying an identical
prompt at temp=0 reproduces the identical wrong output — it does not resample past a deterministic
model error.

**Disposition of the tension named above**: the documented tension itself (recycle=6 calibrated
against `campaign_positioning`'s different, larger shape) is real and worth keeping on record for
future chunk-size/population-scale changes — but the evidence here says it is *not* what broke this
run. `_VOTE_CAST_MAX_CHUNK_SIZE=1` stays shipped (its own chunk-size fix is independently confirmed,
unrelated to this question); `recycle_after_n_calls` stays at its current production value of `6`
(no evidence any other value changes the outcome, so there is no basis to change it). The actual bug
— why the model occasionally produces an internally-incoherent `VoteCastDecision` for a specific
voter, deterministically — is **not** opened as a separate root-cause investigation (see "Scope
disposition" below); it is folded into the existing, broader think=False/decision-quality chantier
this session already identified.

## Mitigation: temperature-varied retry (shipped 2026-08-22)

Since the failure is deterministic at temperature=0 (see above), an identical byte-for-byte retry
(`_complete_and_decode_with_replay`'s own shipped default) cannot resample past it — confirmed
directly by the crashed run's own 2 replay attempts, both failing identically. Per instruction, the
fix is a **local, deliberate, narrowly-scoped exception** to this project's own temperature=0
determinism requirement — not a general retry-policy change — applied only at `cast_votes`'s own
call site:

- `LlmClientProtocol.complete_json`/`OllamaJsonClient`/`VllmJsonClient` gain an optional per-call
  `temperature: float | None = None` override (`None` preserves the client's own configured value,
  byte-identical to today for every existing caller).
- `_complete_and_decode_with_replay` gains `retry_temperature`/`retry_info` (both `None` by default,
  every other decision type unaffected). The **first attempt always uses `temperature=None`**
  (unconditional, does not depend on `retry_temperature` being set) — determinism is preserved on
  the common, successful-first-try path for every decision type, including `cast_votes`. Only a
  genuine retry (attempt ≥ 1) uses `retry_temperature`, when given.
- `cast_votes` is the **only** call site that sets `retry_temperature` (`_VOTE_CAST_RETRY_TEMPERATURE
  = 0.3`, `llm_behavior_engine.py`).
- `VoteBatchOutcome.retry_sampling_varied: dict[int, bool]` (cid → whether that voter's decision came
  from a temperature-varied retry) is journaled as `vote_cast.payload.retry_sampling_varied` (0/1,
  §3.7.1 convention) — a future analysis of the journal cannot mistake a varied-sampling retry's
  decision for an ordinary, deterministic first-attempt one.

**Validated directly against the real production path** (not a reimplementation), using the two
known-reproducible cases from the harness experiment above:
- **cid=7**: first attempt failed with the *identical* error text as every prior observation
  (deterministic reproduction confirmed again); the retry at temperature=0.3 succeeded
  (`blank=0, ranking=[2]`), `retry_sampling_varied=True`. One clean, direct before/after
  confirmation.
- **cid=28**: did **not** reproduce its earlier failure across 3 fresh calls in this validation
  (succeeded at temperature=0 every time) — consistent with this project's own already-documented
  finding that temperature=0 + a pinned seed is *not* a reproducibility guarantee on this inference
  backend (`llm_client.py`'s own module docstring, `ollama_structured_output_results.md`), not
  evidence against the mitigation, but honestly inconclusive as a second data point.

One clean confirmatory case, one inconclusive case — not an exhaustive sweep, per the deliberately
quick validation this was scoped to. Full test coverage (offline, no live model): `test_polity_
llm_client.py` (temperature override reaches the request body, both endpoints, both clients),
`test_polity_llm_behavior_engine.py` (retry_temperature/retry_info contract, cast_votes-specific
wiring, every other decide_* entry point provably unaffected), `test_polity_run_simulation.py`
(the journal marker end-to-end through a real `run_simulation` call).

**A real regression was caught and fixed during implementation**: `OllamaJsonClient._recycle`'s own
re-warm calls (bug 4's mitigation) called the two private `_complete_json_*` methods positionally;
adding a required `temperature` parameter to those methods without updating `_recycle` would have
silently broken every re-warm call (`TypeError`, caught and logged by `_recycle`'s own best-effort
`except Exception`, degrading bug 4's mitigation silently in every `recycle_after_n_calls`-enabled
run, including this project's own acceptance runs). Caught by the existing
`test_recycle_triggers_before_the_call_that_reaches_the_threshold` test failing during this change's
own verification pass, not discovered live. Fixed before this mitigation shipped.

## Scope disposition (per explicit instruction)

This specific bug — a deterministic, per-voter `VoteCastDecision` schema incoherence under
`think=True` — is a concrete, well-documented instance of the broader, already-identified problem in
`reasoning_budget_and_decision_quality_findings.md` (decision-quality/incoherence issues that
structural validation catches for some decision types and not others). It is deliberately **not**
opened as its own root-cause investigation here; it is added to that document's own "Next priority"
workstream scope instead, so it is investigated once, together with the rest of that gap, rather than
piecemeal.
