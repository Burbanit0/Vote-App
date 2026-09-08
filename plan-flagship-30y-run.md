# Plan — the flagship run: 30 simulated years at population 500

> **Living document.** Unlike the other `plan-*.md` files here, this one is a
> *tracker*: every phase carries a status line that is updated as the work
> lands, so the state of a multi-day effort survives a lost session. Written in
> English to match the document lineage it continues (`scripts/vllm_*_results.md`,
> `scripts/check_vllm_*_results.md`), not the French of the older plans.
>
> **Status legend**: `TODO` · `IN PROGRESS` · `DONE` · `BLOCKED` · `DROPPED`

**Overall status: Phases 0, 0bis, 1, 3, 4 and 5 DONE. Phase 2 FAILED its own gate
(does not ship) — the flagship runs sequential, and Phases 3/4 are what make that
survivable and watchable. Starting Phase 6.**
(last updated 2026-09-07)

| Phase | What | Status |
|---|---|---|
| 0 | Pre-flight: disk, provider switch, baseline timing | **DONE** — real baseline measured, 2266.8s/8 ticks |
| 0bis | **NEW**: `vote_cast` needed a seed override AND a deterministic fallback on vLLM | **DONE** — fixed, confirmed on a clean re-run |
| 1 | Re-test the 3 collapse-flagged decision types under vLLM | **DONE** — 2/3 still collapse, 1/3 cleared |
| 2 | Concurrency unlock + byte-identical determinism proof | **FAILED — does not ship.** vLLM concurrency breaks reproducibility too |
| 3 | Checkpoint / resume | **DONE** — verified with a real `kill -KILL` mid-run, byte-identical resume |
| 4 | Observability (`progress.json`) | **DONE** — verified live, incl. a real `kill -KILL`/`--resume` cycle |
| 5 | v3 scale gate at population 500 | **DONE** — sortition + arity + hard-cap + Class B measured |
| 6 | UI-ready output (`snapshots.py`, `viz_export.py`) | TODO |
| 7 | The staged ramp and the flagship run | TODO |

> **The plan survived contact with a real run for four minutes.** That is the
> point of Phase 0 doing a real run first, and the two things it found are both
> recorded below as their own phases rather than folded silently into the work:
> Phase 0bis (found, measured, fixed, tested) and a correction to Phase 5's cost
> assumption (also resolved).

---

## Context

The polity simulator (`fast_api_voter/api/domain/polity/`, 11k lines, 21 modules)
is feature-complete through roadmap palier v7: elections, legitimacy, mandate
drift, petitions, street pressure, exogenous events, social contagion, a
sortition chamber, and multi-round coalition negotiation all exist and are
tested. Nine LLM decision types drive citizen and representative behaviour.

But **it has never been run at the scale it was designed for.** Every LLM run
ever executed is population 100 / 8 years / one seed. The design doc's own
headline — 30 years, 1000 citizens — was priced at ~34h, deferred, and never
attempted. The goal now is a **30-year run at population 500** (with 1000 as the
follow-on), producing artifacts a React UI can consume, so the UI work can start
against real data rather than a fixture.

Three things block that today:

1. **Runtime.** This was originally extrapolated from the *Ollama* measurement
   of 16,670s (4.6h) for pop 100 / 8 years / full features, to ~65-82h
   sequential at pop 500/75 seats. **Corrected by Phase 0's own real vLLM
   measurement** (`plan-flagship-30y-run.md` Phase 0): a rough ~35.6h
   sequential at the same scale — cheaper per-decision on vLLM than the
   Ollama-based estimate assumed, but a linear-scaling projection from one
   data point, not a second measurement. **Concurrency does not reduce this**:
   Phase 2's own determinism proof found vLLM concurrent batching breaks
   reproducibility too (20/497 events diverged, workers=1 vs workers=8, a
   real ~4% divergence rate, not a script artifact — see that phase's own
   writeup), so the flagship runs sequential. ~35.6h (or whatever Phase 7's
   own scale-probe stage actually measures) is the real number to plan
   around, not a speedup on top of it.
2. **No durability.** `run_simulation()` is one in-process `for tick in ...` loop
   holding all state (citizens, parties, 4 RNG streams, `economy_x`, `graph`,
   `pending_rerun`) in local variables. A crash at hour 60 forfeits everything.
3. **No output surface.** Polity has zero API routes, zero UI, and the two
   modules the design doc's architecture names for visualisation
   (`viz_export.py` §14, `snapshots.py` §16.4) do not exist.

## Decisions taken

| Question | Decision |
|---|---|
| Population | **500** now, 1000 as the mid-term goal |
| Provider | **vLLM** (platform blocker cleared; determinism + truncation fix landed this week) |
| Throughput | **Unlock intra-run concurrency**, gated behind a byte-identical determinism proof |
| Features | **Full richness** — every substantive flag ON, including the sortition chamber |
| Collapse-flagged types | **Re-test under vLLM first**, then decide on remediation |
| UI data | **Both** — cheap yearly in-run snapshots *and* a post-run exporter |
| Sortition chamber | **~75 seats (15% of pop)** — middle ground between institutional character and cost |
| `max_batch_replays` | **2**, matching every prior acceptance run (accepts non-byte-reproducibility) |
| Priorities | must not die mid-run > observable while running > UI-ready output |

### Cost consequence of the 75-seat decision

`chamber_deliberation` is one LLM call per seat, **every tick**, and is
population-independent otherwise. At 121 ticks:

| Seats | Calls | Sequential @ 6.9s |
|---|---|---|
| 30 (shipped) | 3,630 | ~7h |
| **75 (chosen)** | **9,075** | **~17h** |
| 150 (30% ratio) | 18,150 | ~35h |

This makes the chamber the **second-largest cost** in the run after
`pressure_action`, and pushes the sequential total to roughly **75-82h**
(this table's own per-call estimate of 6.9s is the pre-Phase-0 Ollama-based
figure; Phase 0's real vLLM measurement revises the overall total down to a
rough ~35.6h — see the Context section above). This table was the strongest
single argument FOR attempting Phase 2's concurrency unlock; Phase 2's own
determinism proof then found vLLM concurrency unsafe for this run (see below),
so the run proceeds sequential regardless — this cost stands as measured, not
mitigated.

## Why concurrency looked like the right lever (correction: it wasn't, see Phase 2)

> **This section's own hypothesis was tested and disproven — Phase 2's
> determinism proof found vLLM concurrency breaks reproducibility too (20/497
> events diverged, workers=1 vs workers=8), for a mechanism outside every
> property named below.** Kept here, unedited, because the reasoning was
> genuine and every individual claim below is still true — it just wasn't the
> complete list. All five properties are about THIS project's own code
> (RNG ordering, chunk partitioning, journaling, per-chunk validation, the
> shared call path). None of them says anything about vLLM's own server-side
> floating-point behavior under concurrent GPU batch composition — the actual
> mechanism the proof implicates. A correct argument about this codebase
> was never going to be sufficient for a claim about the inference server's
> own internals; that gap is exactly why this plan insisted on a live proof
> rather than shipping on the argument. See
> `scripts/check_intra_run_concurrency_determinism_results.md` for the full
> finding and Phase 2's own entry below for the disposition.

`_check_supported()` (`llm_behavior_engine.py:444-458`) hard-refuses
`parallel.intra_run_workers != 1`, citing `llm_batching_determinism_results.md`.
That guard is correct — **for Ollama**, which demonstrably diverges at concurrent
batch ≥5. The config's own comment states the precondition verbatim: *"ne pas
augmenter avant validation du point ouvert n°20 (déterminisme vLLM sous
batching)"*.

**Point ouvert #20 was validated this week.** `scripts/vllm_determinism_results.md`:
byte-identical output at concurrent batch sizes 1/5/25/50, across a full
container restart.

Five independent structural properties make the unlock clean, all verified by
reading the code:

1. **RNG streams are never consumed in LLM phases.** `rupture_rng`, `events_rng`,
   `sortition_rng` are used only in phases 1, 2 and 5 (rupture draws,
   Poisson/AR(1) events, sortition rotation). `accountability.py` and
   `awakening.py` contain zero RNG usage. Parallel LLM calls cannot perturb draw
   ordering.
2. **Work partitioning is already timing-independent.** `chunk_voters()` is
   documented as *"a pure function of (voter set, max_batch_size) — independent
   of arrival order or timing"* — exactly what `batch_sharding: static`
   guarantees.
3. **Journaling is already decoupled from call order.** The call sites journal by
   iterating `outcome.decisions` *after* the decisions are computed
   (`run_polity_simulation.py:745, 873, 1114`), not inside the LLM loop.
4. **Per-chunk ordering is enforced.** `decode_*_batch` requires exactly one
   decision per cid sent, in the same order — a count or order mismatch is a
   full-batch failure.
5. **`_complete_and_decode_with_replay()` is the single shared call path** for
   all nine decision types, so the pool goes in one place.

**This is still a change to a documented reproducibility invariant, and it does
not ship on argument — it ships on the proof in Phase 2.**

---

## Phase 0 — Pre-flight · **DONE**

- [x] **Disk**: reclaimed via `docker builder prune -f` (8.2GB) plus a removed
      duplicate/orphaned HF-cache volume — 18G → 25G+ free. Done surgically,
      not via a blanket `docker system prune`, to keep the stopped
      `vllm-polity` container intact.
- [x] **Provider switch**: `polity_config.yaml` `provider: ollama` → `vllm`,
      `base_url` → `http://localhost:8000/v1`. Shipped in
      `35e41bb feat(polity): switch the shipped LLM provider to vLLM`.
- [x] **Baseline timing, measured for real** — 3 attempts, see Phase 0bis for
      why the first two crashed and what fixed them. The third
      (`baseline-2y-p100-vllm-v3`) completed cleanly: 2 years / pop 100 /
      seats 30, full richness, `max_batch_replays=2`.

  | | Value |
  |---|---|
  | Wall-clock | 2266.8s (~37.8 min) over 8 ticks |
  | Seconds/tick | 283.35s |
  | Decisions | 632 total (100 candidacy, 100 vote_cast, 270 chamber, 137 pressure, 8 coalition, 7 response, 5 nomination, 5 positioning) |
  | Replays | 188 log lines / **42 actual replay events** (multi-line pydantic errors inflate a naive line count ~4.5x) — all 42 recovered, 0 fallback activations needed in this run |

  **Corrected flagship cost projection.** Every prior number in this plan
  (the 65-82h range) was extrapolated from *Ollama* per-call costs. Scaling
  this real vLLM measurement per decision type (population-linear for
  candidacy/vote_cast/pressure_action, seat-linear for chamber, ~flat for
  party/officeholder-level types) projects **~35.6h sequential** for
  30y/pop 500/seats 75 — meaningfully cheaper than the Ollama-based estimate,
  though still firmly in "needs Phase 2's concurrency unlock to be practical"
  territory, and this is a rough linear-scaling model, not a second measured
  data point. The Phase 7 scale-probe stage (8y/pop 500) is what actually
  confirms or corrects this.

**Gate met**: `run_metadata.json` records `llm_provider: vllm`, `llm_model:
qwen3:8b`; the 2-year run completed and `index_run()` produced `metrics.json`
with no errors.

## Phase 0bis — the `vote_cast` retry needed a seed override on vLLM · **FIXED**

Not in the original plan. Found by Phase 0's own first real LLM arm, which died
4 minutes in, in tick 0's presidential election:

    LlmResponseError: batch failed schema validation: 1 validation error for
    VoteCastBatch decisions.0
      Value error, blank=1 requires an empty ranking (§3.6.1 hard rule)

The defect itself is old and documented — `cache_recycle_chunk_size_tension_
findings.md` characterises `blank=1` + non-empty `ranking` as a **deterministic,
per-voter-prompt** model error at temperature=0 — and it ships with a mitigation:
`_VOTE_CAST_RETRY_TEMPERATURE = 0.3`, a deliberate, narrow exception to the
temperature=0 rule, so a retry can *resample past* an answer an identical retry
would only reproduce.

**Initial hypothesis, revised by the full measurement.** A first, narrow read of
the crash's own replay log (cid 24 failing twice, byte-identical, at temp 0.3)
suggested the mitigation was structurally inert on vLLM. The full 2x2 against 9
real production-shaped failures says something more precise: it is not inert, but
it is not reliable either.

| Retry condition | Total recovery (of 27 attempts) | Voters left stuck (of 9) |
|---|---|---|
| temp 0.3, pinned seed (**shipped**) | 74.1% | 1 |
| temp 0.3, varied seed | 70.4% | **0** |
| temp 1.0, pinned seed | 66.7% | 3 |
| temp 1.0, varied seed | 59.3% | 1 |

The shipped mitigation actually has the *highest* raw recovery rate — but it is
the only one (besides temp-1.0-varied) that leaves a voter fully stuck (0/3
recovered across 3 otherwise-identical attempts). That stuck case is exactly what
the crash hit: not "the mitigation never works," but "it doesn't always work, and
production only budgets 2 retries." Varying the seed on retry — keeping
temperature at 0.3, not raising it — is the one condition with zero stuck voters
in this sample.

**Root mechanism, also more precise than the first pass**: `VllmJsonClient`
pins `seed` on every call, and the class's OWN pre-existing docstring already
anticipated why that matters at temperature>0 specifically: *"seed is sent for
parity with OllamaJsonClient, but at temperature=0 sampling is already argmax; it
does nothing about batch-composition nondeterminism, which is a kernel
floating-point reduction order property, not a sampling one."* At temp=0.3,
sampling is no longer robust to that per-call float noise the way argmax is — so
"same seed, same temperature" is close to but not exactly deterministic on long,
complex, `think=True` generations, which is why the shipped mitigation recovers
*most* of the time without recovering *every* time.

**Why it never surfaced on Ollama**: Ollama's own non-reproducibility (already
documented — *"temperature=0 + a pinned seed is not a reproducibility guarantee on
this inference backend"*) meant a same-seed retry always varied there anyway. The
shipped mitigation's own validation reflects that thinness: one clean confirmatory
case (cid=7) and one inconclusive one, both on Ollama, never exercising the
regime this measurement did.

**Reproduction**: `scripts/check_vllm_vote_cast_retry_is_inert.py` /
`scripts/check_vllm_vote_cast_retry_is_inert_results.md`, driving the real
production path (`build_system_prompt`/`build_user_prompt`,
`VOTE_CAST_JSON_SCHEMA`, `decode_vote_batch`, the shipped budget and chunk-size-1
shape) on a same-seed, same-scale reconstruction of the crashed run's tick-0
world (not byte-exact — nominee selection uses a simplified tie-break, so the
specific failing cid differs — but the 36% base rate and the general
retry-reliability phenomenon are real and reproduce independent of that detail).
Also surfaced: 2 of 9 failures were `finish_reason='length'` token-budget
truncations, not the blank/ranking defect at all — a second, distinct failure
mode worth watching but not chased further here.

**Fix, shipped**: `_complete_and_decode_with_replay` gained `retry_seed_base`,
mirroring the existing `retry_temperature` — on retry, `seed = retry_seed_base +
attempt`, a different seed every attempt, never repeating the first attempt's or
each other's. `cast_votes` now sets both `retry_temperature=0.3` (unchanged) AND
`retry_seed_base=_VOTE_CAST_RETRY_SEED_BASE` (new). Both `OllamaJsonClient` and
`VllmJsonClient` gained a matching `seed` override on `complete_json`, symmetric
with the existing `temperature` override. 1204 polity tests pass (12 new/updated
for this change), mypy clean. Determinism cost is already accounted for: a run
with `max_batch_replays > 0` is documented as not byte-reproducible regardless,
and Phases 2/3 run their determinism proofs at `replays=0`, where this override
never fires (attempt==0 always uses `seed=None`).

**Not fully closed**: n=9 is a small sample. The fix is evidence-based (best
available data), not proven to eliminate every stuck case at flagship scale
(500 citizens x 8 elections x chunk-size-1 = 4,000 vote_cast calls). The Phase 0
baseline re-run is the real test.

**The re-run confirmed the residual risk, not a clean pass.** The seed-varying
retry demonstrably worked for 4 of 5 voters that failed their first attempt in
the re-run (cid 7, 12, 16, 24 all recovered on a later, differently-seeded
retry) — the mechanism is real. But cid 33 failed **identically** across both
retry seeds (900000002 and 900000003), same wrong ranking both times, and the
run crashed again. This is the exact shape the first measurement's aggregate
stats already implied (1 of 9 stuck even under the best condition) — not every
seed change actually diversifies a temperature-0.3 sample for every prompt.

**Second fix, shipped alongside a graceful-degradation design change**:
`cast_votes` now catches `LlmResponseError` around its whole per-chunk block
(the retry call AND `validate_decision`) and, on exhaustion, falls back to
`simple_rules.build_ranking` — the exact deterministic function cast_votes's own
module docstring says it replaced — for that one voter, rather than raising and
killing the run. This applies at ANY `max_batch_replays` setting, including 0:
the fallback is a zero-LLM-cost mechanism, not itself a replay, so it isn't
gated by how much retry budget is configured.

The fallback's motif is not a placeholder: `build_ranking`'s own
within-blank-threshold test is exactly what `VoteMotif.ACCEPTABLE_MATCH`/
`NO_MATCHING_PRIORITY` distinguish, so the reported code is an accurate
classification of the ballot actually produced, computed structurally instead
of by model judgment. Provenance is tracked honestly: a new
`VoteBatchOutcome.llm_fallback: dict[int, bool]` field, journaled as
`vote_cast.payload.llm_fallback` (mutually exclusive with
`retry_sampling_varied`), so no future analysis mistakes a fallback ballot for
a real model decision. 1205 polity tests pass (7 more new/updated for this
second change), mypy clean.

**This directly implements the plan's own stated priority order** ("must not die
mid-run" > observable > UI-ready output) rather than just asserting it — the
first thing that would have died mid-run now degrades instead.

**Confirmed on the real re-run** (`baseline-2y-p100-vllm-v3`, same population/
seed as the two crashed attempts): completed end-to-end, 100/100 `vote_cast`
decisions produced, 42 first-attempt failures, **all 42 recovered via the
seed-varying retry, 0 fallback activations needed**. Notably, the specific
voter that got permanently stuck in the v2 crash (cid 33, identical wrong
answer across both retry seeds) did NOT reproduce that behaviour here, despite
identical population/seed/config — consistent with this project's own standing
finding that vLLM's near-tie sampling behaviour is batch-composition/cache-state
sensitive, not a pure function of the declared seed. Not chased further: the
fallback's whole point is that this doesn't need explaining to be safe.

**Deliberately NOT done**: the same treatment for the other 8 decision types.
Several have their own `simple_rules.py` deterministic equivalent already
(`deterministic_pressure_action`, `deterministic_reaction_to_event`,
`select_party_nominee`, `form_coalition`, `build_confidence_ballot`) — the same
mechanism could extend to them relatively mechanically. This is scoped out for
now because only `vote_cast` has actually been measured to fail this way; adding
speculative fallbacks to 8 more call sites without evidence they need one would
be exactly the kind of unrequested generality this project's own conventions
argue against. **Flagged as a real, named risk for the flagship**: any of those
other 8 types could crash a 30-year run the same way `vote_cast` did, and this
has not been checked. Phase 1 (re-testing the collapse-flagged types) is a
natural place to extend this check before the real run, not assumed safe by
default.

## Phase 1 — Re-test the three collapse-flagged decision types under vLLM · **DONE**

`representative_response` (dt=6), `reaction_to_event` (dt=8, scandal branch) and
`coalition_decision` (dt=9) each carry a `RELIABILITY WARNING` block:
structurally opposite input poles produced byte-identical decisions (4/4, 6/6,
6/6). **All three were measured on Ollama only.** Different weights (AWQ) may
behave differently — the truncation bug already proved backend-specific
behaviour is real.

Re-ran the existing collapse-signature scripts, pointed at vLLM (new
`check_vllm_*_collapse_signature.py` variants, client class swapped only):
full results in `scripts/check_vllm_collapse_signatures_results.md`.

**Result: 2 of 3 still collapse, 1 of 3 does not.**

| Decision type | vLLM/AWQ | Verdict |
|---|---|---|
| `representative_response` | 6/6 identical (CONCESSION), both poles | Confirmed — stays `unverified` |
| `coalition_decision` | 6/6 identical (JOIN), both poles | Confirmed — stays `unverified` |
| `reaction_to_event` (SCANDAL) | VARIES: 0.20 (low salience) vs 0.15 (high salience), directionally sensible | **Warning dropped** |

Two collapses surviving a full backend + quantization change rules out "Ollama
serving artifact" as the explanation for those two — points toward the model's
own learned behaviour on those specific prompt shapes, not infrastructure. Not
root-caused further here, same discipline as elsewhere in this investigation:
this measures whether the warning still applies, not why.

**Decision gate applied**: `representative_response`/`coalition_decision` stay
`unverified` in any exported flagship artifact (Phase 6) — the UI must not
present metrics derived from them as trustworthy. `reaction_to_event`'s SCANDAL
branch warning is dropped (the `ECONOMIC_SHOCK` branch was never in scope for
either version of this check).

**Cost**: ~1 minute of GPU time for all three (18 calls total, `think=False`,
size=1). Done before spending days of GPU on the flagship, as planned.

## Phase 2 — Concurrency unlock + determinism proof · **IN PROGRESS**

**Structural finding, from actually reading the code rather than assuming**: only
5 of the 9 decision types chunk at all (`cast_votes`, `decide_candidacies`,
`decide_pressure_actions`, `decide_reaction_to_event`, `decide_chamber_
deliberation`) — confirmed by grep, not inferred. The other 4
(`decide_party_nominations`, `decide_campaign_positioning`,
`decide_representative_response`, `decide_coalition`) make exactly one call per
tick over a small officeholder/nominee/party count; there is nothing to
parallelize WITHIN a tick for them. This exactly matches the plan's own
"highest-value targets" list — not a coincidence, that list *is* the chunking
decision types.

**Shipped so far**:
- `_check_supported()`'s blanket refusal is now provider-conditional: still
  refuses `intra_run_workers > 1` on Ollama (the finding that guard exists to
  protect against), allowed on vLLM.
- A new shared helper, `run_chunks()`, is the single execution strategy behind
  all 5 chunked decision types: `workers=1` is a plain sequential loop (not
  merely a 1-worker thread pool — byte-for-byte the same code every prior
  config ran), `workers>1` submits every chunk to a bounded
  `ThreadPoolExecutor` and returns results **in chunk order, never completion
  order** — the exact property the journal's own downstream ordering depends
  on.
- Threads, not the `asyncio.gather` mechanism `vllm_determinism_results.md`'s
  own proof used — deliberately not assumed equivalent by that fact alone
  (see `run_chunks`'s own docstring for why the client-side mechanism doesn't
  matter to the server-side claim being tested). This is exactly why Phase 2
  ships on its own dedicated proof, not by citing that one.
- All 5 chunked `decide_*` functions refactored to build a per-chunk worker
  closure and route it through `run_chunks`. Reaction_to_event's own
  RELIABILITY WARNING docstring updated in place to reflect Phase 1's finding
  (SCANDAL branch collapse resolved on vLLM).
- Unit tests: `run_chunks` itself (order preservation under real concurrency,
  unchanged sequential behavior at workers=1, exception propagation, empty
  input) plus the 9 existing `_check_supported` guard tests split into
  `_on_ollama` (still raises) + one shared vLLM positive case. 1211 polity
  tests pass, mypy clean.
- `scripts/check_intra_run_concurrency_determinism.py` written: runs the
  flagship's own full-richness config twice (`workers=1` vs `workers=N`,
  `max_batch_replays=0` — a run with replays>0 is already documented as not
  byte-reproducible, entangling that with a concurrency question would make
  a diff impossible to attribute), diffs `events.jsonl` byte for byte.

**Smoke-scale proof ran (1 year/pop 100/seats 30/workers 8, replays=0).**

First result was a **false FAIL**: `filecmp.cmp` flagged every line as different, but
the only actual difference was the `run_id` field itself
(`determinism-1y-p100-w1` vs `...-w8`) — a bug in the check script, not a
finding: `run_id` is baked into every journal line and I'd used a different one
per arm. Fixed (`run_arm` now uses the SAME `run_id` across arms, kept apart by
`output_dir` instead) before drawing any conclusion from it.

**With `run_id` normalized out of the already-computed journals**: 20 of 497
events (~4%) still differ, all `vote_cast`, and all the SAME shape — payload's
`llm_fallback` flips 0↔1 between arms (the voter succeeded on the first LLM
attempt in one arm, failed and fell back in the other), while **`ranking`/
`blank`/`motif` are byte-identical in every one of the 20 cases**. Not a
different vote — a different MECHANISM producing the same vote, this time.

**Consistent with, not yet proof of**, vLLM's own documented mechanism
(`llm_client.py`'s class docstring, already on record before this proof):
argmax at temperature=0 is normally robust to per-call floating-point noise,
except at a genuine near-tie branch point, where kernel-level floating-point
reduction order — itself a function of GPU batch composition, which
concurrency changes by construction — can flip the result. 20/497 near-tie
flips is a small, plausible rate for exactly that mechanism.

**Control run: two sequential `workers=1` runs, same seed/config, diffed against
each other — 0 of 497 events differ.** This rules out inherent, load-independent
vLLM/AWQ non-determinism and confirms the 20/497 divergence against `workers=8`
is attributable to concurrency specifically. Also measured precisely: `vote_cast`'s
first-attempt failure rate was 30/100 identically in BOTH sequential runs, and
39/100 under `workers=8` — concurrent load doesn't just reshuffle which citizen
fails, it makes failure measurably more likely.

## Phase 2 verdict: FAIL. Does not ship.

Full writeup: `scripts/check_intra_run_concurrency_determinism_results.md`.

Per the plan's own pre-registered gate ("Any diff => the unlock does not ship"):
`_check_supported()`'s refusal of `intra_run_workers > 1` is **unconditional
again**, now citing both the original Ollama finding and this new vLLM one.
`run_chunks()` and the 5 refactored `decide_*` functions **stay in the
codebase** — correct, unit-tested in isolation, and proven byte-identical to
the pre-Phase-2 sequential code at the only value `_check_supported` now ever
allows through (`workers == 1`). Deliberately not reverted: nothing about this
finding says the mechanism itself is wrong, only that the gate must not open it
yet. Re-enabling it needs either a fix to the underlying batch-composition
sensitivity (vLLM/CUDA-level instrumentation this project doesn't have) or a
separate, deliberate policy decision to accept a ~4% divergence rate — neither
decided here.

**Consequence for the flagship**: it stays sequential. Phase 0's real
measurement (2266.8s for 2y/pop100) is the throughput to plan around, not the
~3.5x speedup this proof's own timing showed before being disqualified on
correctness grounds. Phase 3 (checkpoint/resume) moves from "nice to have
alongside concurrency" to the only mitigation for a multi-day sequential run —
exactly the plan's own pre-registered risk-section fallback, now the live path.

**Change**: add a bounded worker pool for independent LLM calls within a tick,
gated to `provider == "vllm"`, driven by the existing `parallel.intra_run_workers`
config key.

- Replace the blanket refusal in `_check_supported()` with a provider-conditional
  one: >1 workers allowed on vLLM, still refused on Ollama with the existing
  message and citation.
- Parallelise at the **chunk/call level inside each `decide_*` function** — the
  natural unit, since `chunk_voters()` already produces the deterministic
  partition. Highest-value targets in order: `pressure_action` (dominant cost),
  `chamber_deliberation` (9,075 calls at chunk=1, 75 seats × 121 ticks),
  `vote_cast` (4,000 calls at chunk=1), `reaction_to_event`,
  `candidacy_considered`.
- **Collect results into a list indexed by chunk position, then return in
  canonical order.** Never journal from inside a worker.
- Keep `_complete_and_decode_with_replay()` as the per-call unit so replay/retry
  semantics, `_VOTE_CAST_RETRY_TEMPERATURE`, and error classification are
  unchanged.
- Note the interaction with `max_batch_replays`: a run with replays > 0 is
  already documented as not byte-reproducible. The determinism proof must run
  with `replays=0`.

**The proof (this is the gate, not a formality)**: run the same seed and config
twice at 2 years / pop 100 — once `intra_run_workers=1`, once `=8` — and diff
`events.jsonl` **byte for byte**. Identical bytes ⇒ ship. Any diff ⇒ the unlock
does not ship, and the plan falls back to sequential + checkpointing.

Commit the proof as `scripts/check_intra_run_concurrency_determinism.py` plus a
results doc, matching this project's existing convention that a results doc ships
with real measured numbers.

**Also worth testing here** (cheap, potentially large):
`_VOTE_CAST_MAX_CHUNK_SIZE` and `_CHAMBER_MAX_CHUNK_SIZE` are both pinned to `1`
purely because of *Ollama* failures documented in-code. If vLLM tolerates
chunk >1, that is a further multiple on top of concurrency. Test it; only raise
it if clean.

## Phase 3 — Checkpoint / resume · **DONE**

**Shipped**: `api/domain/polity/checkpoint.py` (new module) + `run_simulation`'s
own `resume: bool = False` parameter + `run_polity_flagship.py`'s `--resume`.

**One refinement from the original plan, found by reading the actual code
rather than assuming**: `graph` (the social graph) and `InstitutionalClock`
are NOT checkpointed. Both are pure functions of `(config, population_size,
seed)` with zero mid-run mutation (`social_graph.py`'s own docstring:
"generated once... this never changes mid-run"; `InstitutionalClock.from_config`
takes config alone, holds no state) — regenerating either from the resumed
config reproduces them exactly. Snapshotting them would be pure duplication
with its own resync risk, not a correctness requirement. What IS captured,
exactly as planned: `citizens` (every field, including `chamber_position`,
`petition_signers`, role/office), `parties`, `pending_rerun`, `economy_x`,
`mobilized_last_tick`, and the three RNG streams that actually persist across
ticks (`rupture_rng`, `events_rng`, `sortition_rng` — the social graph's own
generation RNG is fully consumed once, before the tick loop starts, so there
is no fourth persistent stream to restore).

**Checkpoint written to `<journal.output_dir>/<run_id>/checkpoint.json`**
(atomic: `.tmp` + `os.replace`), after every tick's phases are fully done and
journaled — never mid-tick, so a resume always restarts a tick from its own
beginning. `journal.truncate_journal` discards any events a crash left behind
from a tick that started but never finished (and therefore never got its own
checkpoint) before the resumed `Journal` reopens the file with
`start_event_id` set to the checkpoint's own `next_event_id`, continuing the
id sequence rather than restarting it at 0 (a `Journal.__init__` gap that
would otherwise corrupt a resumed file's event ids). `resume=True` verifies
both `run_id` and `checkpoint.config_hash(config)` match before touching
anything, and refuses loudly (not silently) on either mismatch.
`resume=False` (every pre-Phase-3 caller, unaffected) now also refuses if a
checkpoint already exists at that path — the same "don't silently clobber
resumable progress" discipline the runner's own collision guard already had
for a fresh run_id.

**A real efficiency bug found and fixed along the way**: the first working
version serialized each `Citizen` via `dataclasses.asdict()`, which slowed
the polity test suite by 3.3x (37s -> 123s) purely from checkpointing every
tick of every `run_simulation` test. `asdict()`'s generic recursive
implementation deep-copies every field defensively — wasted work for
`Citizen`, a flat dataclass with no nested dataclass fields. Switched to
`vars(citizen).copy()`: measured 303x faster (3.2ms -> 0.011ms per
100-citizen pass), test suite back to 68s. Production impact is negligible
either way (a real flagship tick costs 283-1069s+, GPU-bound) — this was
purely a test-iteration-speed fix, caught by measuring rather than assuming
the first working version was fast enough.

**Gate, met three ways**:
1. Unit tests: `checkpoint.py`'s own round-trip (every citizen field,
   parties, pending_rerun, RNG stream continuation, config-hash sensitivity)
   and `journal.py`'s `truncate_journal`/`start_event_id`/`next_event_id`.
2. Integration (pytest, in-process): a real config (RNG-consuming phases,
   citizen-mutating mechanisms, a real social graph, a sortition chamber)
   interrupted by an injected exception — once mid-tick (after some of that
   tick's own phases had already journaled, proving truncation), once
   cleanly between ticks (proving the no-partial-data case too) — resumed,
   and diffed byte-for-byte (run_id excluded) against an uninterrupted run.
   Both match exactly.
3. **The real-world case, not just pytest**: a live `run_polity_flagship.py`
   process, actually `kill -KILL`'d mid-run (tick 52 of 120, 1000 citizens/
   30 years/deterministic engine), resumed via the actual `--resume` CLI
   flag, and diffed against an uninterrupted reference — 17,791 events,
   **zero diffs**.

## Phase 4 — Observability · **DONE**

**Shipped**: new module `api/domain/polity/progress.py` (`ProgressTracker` +
`write_progress`), wired into `run_simulation`'s tick loop at the same point as
Phase 3's own checkpoint write. `progress.json` lands beside `checkpoint.json`
in the run's own directory, rewritten atomically after every tick.

Fields, all shipped as specified: `tick`, `total_ticks`, `simulated_year`,
`wall_clock_elapsed_seconds`, `last_tick_duration_seconds`,
`avg_recent_tick_duration_seconds` (a 10-tick rolling window, not a whole-run
average — tick cost is genuinely heterogeneous, an election/coalition/chamber
tick costs far more than a routine one, so a flat average would converge
slowly and misrepresent the current phase of the run), `eta_seconds` +
`eta_timestamp`, `decisions_by_type`, `decisions_total`, `retry_count`,
`fallback_count`, `last_checkpoint_tick`.

**Design choice, and why**: every cumulative count is re-derived from the
journal itself (an incremental scan via a running byte offset, not
event_id bookkeeping — `Journal.write`'s own synchronous-flush contract makes
a plain `seek`/`tell` sufficient), never tracked as a separately-maintained
running total. This means `ProgressTracker` can never drift out of sync with
what actually happened, and — the real payoff — it makes resume correctness
free: a fresh `ProgressTracker` instance (byte offset 0) constructed in a
resumed process's first call naturally reads everything the truncated journal
already holds from the crashed attempt, backfilling cumulative counts with no
separate "resume mode" or checkpoint-schema extension needed.

**A real bug this surfaced, not introduced**: `run_polity_simulation._run_
reaction_to_event` writes `codebook_version` unconditionally, even on its own
deterministic branch (`llm.enabled=False`) — a pre-existing quirk this
project's own `run_polity_flagship.py._count_llm_decisions` had already found
and worked around (gated to `engine == "llm"`). `ProgressTracker`'s own
"codebook_version is truthy ⇒ LLM decision" heuristic inherited the same false
positive the first time it ran against a real deterministic run — caught by
actually running it end-to-end (a live smoke test), not assumed safe.
Fixed the same way: `ProgressTracker` takes `llm_enabled`, skipping the
count (never the byte-offset advance) when false.

**Verified three ways**: `progress.py`'s own unit tests (rolling window,
incremental scanning, resume-backfill-by-construction, the reaction_to_event
false-positive fix), an in-process integration test confirming cumulative
counts survive an injected crash-and-resume, and — again, the real case, not
just pytest — a live `run_polity_flagship.py` process actually `kill -KILL`'d
mid-run: `progress.json` at the moment of the kill showed sensible tick/ETA/
decision-count state, and after `--resume`, cumulative counts correctly
reflected the FULL run's history (2000 → 3000 decisions across the crash
boundary), not just the post-resume portion. 1258 polity tests pass, mypy
clean.

Cheap and high-value, as planned: it turns a 3-day black box into something
watchable, and `progress.json` gives the future UI a live status endpoint for
free (§16.1's "hot regime" without needing the WebSocket yet).

## Phase 5 — v3 scale gate at population 500 · **MOSTLY DONE**

Done early and cheaply, as the plan asks. Full numbers:
`fast_api_voter/scripts/polity_scale_gate_pop500_results.md`, reproducible via
`scripts/check_polity_scale_gate_pop500.py`.

| Question | Answer |
|---|---|
| Sortition pool exhaustion at (500, 75) | **Safe, and better than shipped.** Strict eligibility survives to rotation #7 vs #4 at (100, 30); every rotation fills every seat at both scales |
| `max_candidates_hard_cap: 20` | **Inert.** Parsed by `config.py`, read by nothing — it cannot bind at any population |
| Nomination arity | **4–7 contenders per party at pop 100 → 15–26 at pop 500.** ADR-002's criterion still met, so `ambition_threshold` needs no re-deriving |
| Class B rupture declarations | **17 at pop 100 → 82 at pop 500**, linear in population |

**Still open**: whether the model *decides well* across a ~20-way
`party_nomination_choice` — a decision-quality question no deterministic run can
answer. Folded into the same labelling discipline as Phase 1.

**Correction to this plan's own assumption.** Phase 5 said most of this is
measurable from deterministic runs. Only the sortition question actually was: the
hard-cap and Class B questions need `candidacy.rupture_path_enabled: true`, which
is shipped `false` and which "full richness" was not turning on. Same for
`institutions.blank_vote_competitive`. Both are now set in `_flagship_config`;
`parties.birth_enabled`/`death_enabled` stay off because they are parsed but not
implemented.

`docs/adr/v3-readiness-checklist.md` is an **explicit gate** with Classes B/C/D
unrun. Its own rule: *"'No new parameter' does not mean 'no parameter changes
behaviour.'"* Running the flagship before clearing it produces a result set that
differs from v2 for reasons nobody separated.

At population 500 specifically:

- **`sortition_chamber.seats` → 75 (decided)**. 30 seats would be 6% of the
  population at n=500 versus 30% at n=100 — the checklist's *"a different
  institution, not a scaled one"*. 75 keeps it a recognisably broad citizen
  chamber (15%) at ~half the cost of a full 30%-ratio scaling. **Required
  work**: `sortition_chamber.py`'s pool-exhaustion and relaxed-eligibility
  analysis is explicitly scoped to `population_size=100, seats=30` and does
  **not** transfer — re-measure pool exhaustion at (500, 75) before trusting any
  chamber output. Config guard `sortition_chamber.seats <= population_size`
  still holds comfortably.
- **`ambition_threshold` / party nomination arity** — the 0.30 value was derived
  from 5 parties × ~20 members. At pop 500 each party has ~100 members, so
  `party_nomination_choice` becomes a ~20-way LLM arbitration instead of 4-way.
  The value doesn't need re-deriving; **the mechanism it protects does.**
  Measure contenders-per-party; consider scaling `parties.initial_count`.
- **`max_candidates_hard_cap: 20`** — never binding at n=100; rupture
  declarations scale linearly (~5× at pop 500). Check whether it binds, since it
  would silently convert §2.3's rule-based bounding into an arbitrary numeric
  cap.
- **Class B**: report expected vs observed rupture declaration counts at both
  scales.

Most of this is measurable from **deterministic runs (0.1s each)** — no LLM cost.
Do it cheaply and early.

## Phase 6 — UI-ready output · TODO

**In-run (`snapshots.py`, §16.4)**: once per simulated year, snapshot per-citizen
state — `citizen_id`, `issue_positions` (20 dims), `party_affiliation`,
role/office, `event_salience`, plus holder-specific `pledged_platform` vs
`revealed_position`. At 500 citizens × 30 years that is 15,000 rows — negligible
cost, and it is the only way §14.1 (micro force graph) and §14.2 (méso 2D
projection animated over 30 years) can be built without replaying the entire
journal.

Settles §14.6's open question — *"snapshots generated during the run or in
post-processing?"* — as **both**, deliberately: snapshots are cheap insurance
against discovering post-hoc that the data wasn't captured, on a run too
expensive to repeat.

**Post-run (`viz_export.py`, §14)**: replay journal + snapshots into UI-ready
artifacts:

- **Macro** (§14.3): per-tick time series — legitimacy, effective parties,
  blank-vote rate, mandate deviation, stance distribution, chamber deviation
- **Institutional** (§14.4): timeline of elections, coalitions, petitions,
  recalls, scandals
- **Micro/méso** (§14.1/2): the yearly snapshots, plus the social graph
- **Biography** (§16.7): per-citizen event stream, already queryable from the
  DuckDB view

Reuse `index_run()`/`RunMetrics` rather than recomputing metrics. Respect the
three documented traps in `indexer.py`: `mandate_deviation` is left-censored
(prefer the `ctx` source; check `mandate_deviation_source`), `chamber_deviation`
has length seats×presided_ticks not ticks, and `petition_success_rate` is not the
removal rate. Carry the Phase 1 `unverified` labels through.

`compact_run()` already produces the DuckDB artifact; keep it as the queryable
base.

## Phase 7 — The run · TODO

A runner script `scripts/run_polity_flagship.py`: argparse, `--resume`,
`--years`, `--population`, `--workers`, one flagship arm, writing `config.json` +
`metrics.json` + `progress.json` alongside the journal — following the existing
`run_v7_acceptance.py` / `run_acceptance_comparison.py` conventions.

Staged ramp, each stage gating the next:

1. **Smoke** — 2 years, pop 100, all features. Proves the wiring end-to-end.
2. **Parity** — 8 years, pop 100, all features. **Compare against the existing
   measured baseline** (`acceptance_v6b_results.md`, 16,670s, 28 replays) — this
   is the only apples-to-apples check that vLLM + concurrency didn't change the
   simulation's behaviour, only its speed.
3. **Scale probe** — 8 years, pop 500. Confirms the Phase 5 decisions and gives a
   real per-tick cost at the target population to extrapolate from.
4. **Flagship** — 30 years, pop 500, all features, with checkpointing on.

Then the same path to population 1000 as the mid-term goal.

---

## Verification summary

| Phase | Gate |
|---|---|
| 0 | 2-year vLLM run completes; `run_metadata.json` shows vllm; measured baseline recorded |
| 1 | Three collapse scripts re-run under vLLM; each type labelled verified or unverified |
| 2 | **`events.jsonl` byte-identical, workers=1 vs workers=8, same seed** — **FAILED, does not ship; flagship runs sequential (Phase 3 is now load-bearing)** |
| 3 | **`events.jsonl` byte-identical, uninterrupted vs killed-and-resumed** — **MET**, incl. a real `kill -KILL` |
| 4 | `progress.json` updates per tick; ETA converges — **MET**, incl. a real `kill -KILL`/`--resume` cycle |
| 5 | v3 checklist Classes B/C/D measured at pop 500; seats/initial_count decisions recorded |
| 6 | `viz_export.py` output loads; DuckDB queries return expected row counts |
| 7 | 8-year pop-100 parity vs `acceptance_v6b_results.md`; then flagship completes |

Existing gates stay green throughout: `mypy api/` clean, `flake8`, and the polity
test suite (22 files, ~15.4k lines) — especially `test_polity_run_simulation.py`
(188 tests) and `test_polity_llm_behavior_engine.py` (242 tests), which cover the
code Phases 2-3 touch.

## Risks

- **The determinism proof fails.** ~~Mitigation: it is a gate, not an assumption.
  Fallback is sequential + checkpointing (~3 days in resumable segments) — slower
  but still achievable.~~ **This happened.** Phase 2's proof failed (20/497 events
  diverged, workers=1 vs workers=8) and the pre-registered fallback is now the
  live plan: sequential + Phase 3 checkpointing, not a hedge.
- **Reliability floor is irreducible.** ~6.7% deterministic `vote_cast` failures
  and ~2.6% chamber Mode-A truncations are documented and already mitigated
  (retry at temp 0.3, prompt fix). At 500 citizens × 8 elections plus 9,075
  chamber calls these produce real absolute volumes — expect materially more
  replays than the 11-28 seen at pop 100. `max_batch_replays: 2` (decided) makes
  the flagship non-byte-reproducible, exactly as every prior acceptance run was.
  **The Phase 2 and Phase 3 determinism proofs must therefore run with
  `replays=0`** — they are testing the concurrency and resume machinery, not the
  flagship's own configuration.
- **Scientific validity, not just throughput.** Several decision types are
  quality-unvalidated against ground truth (`pressure_action` sits at 52.9-60%
  vs an ≥80% bar). A longer run produces more of the same unverified numbers.
  This plan labels rather than fixes that — worth an explicit decision if the UI
  intends to present those metrics as findings.
- **Population 1000 is not just 2× of 500.** `sortition_chamber.seats` at 3%,
  ~40-way party nomination arbitration, and `max_candidates_hard_cap` binding all
  get worse. Re-run Phase 5 before the 1000 run rather than assuming it scales.

---

## Execution log

Newest last. One line per landed step, with the commit hash where there is one.

- **2026-09-06** — Plan approved and written down here as a tracker. Starting
  state: branch `polity` at `455db1d`; `provider: ollama` shipped; `vllm-polity`
  container built and validated (`--structured-outputs-config
  '{"backend": "xgrammar", "disable_any_whitespace": true}'`, max-model-len
  16384, gpu-memory-utilization 0.80) but stopped; disk 86% full / 18G free.
- **2026-09-06** (`9dcafa8`, `35e41bb`, `bb00bd9`) — disk reclaimed; provider
  switched to vllm; `run_polity_flagship.py` written and verified deterministically
  at full flagship scale (30y/pop 500, 6.4s, no GPU) before any LLM time was spent.
- **2026-09-06** (`0574205`) — Phase 5 scale gate cleared at population 500:
  sortition safe at 75 seats, nomination arity 15-26/party, `max_candidates_
  hard_cap` found structurally inert (parsed, never read), Class B rupture counts
  linear in population. Exposed and fixed two config gaps in the flagship runner
  itself (missing richness flags; missing run-collision guard).
- **2026-09-06** (`2324c81`) — fixed the run-start LLM warm-up: it was using a
  shape (`"{}"` at `max_tokens=32`) this project's own recycle-path docstring
  already documents as worse than the alternative, and it hard-failed under vLLM.
- **2026-09-06** — first real LLM arm of the flagship plan (2y/pop100/vllm)
  crashed in tick 0's presidential election: `vote_cast`'s shipped temperature-
  varied retry mitigation turned out to be inert against vLLM's pinned-seed
  determinism. Measured the mechanism directly
  (`check_vllm_vote_cast_retry_is_inert_results.md`, 9 real failures): the
  shipped retry recovers 74% of attempts but leaves 1 of 9 voters fully stuck.
- **2026-09-06** (`95b5552`) — fix #1: vary the retry seed alongside the retry
  temperature. Re-run recovered 4 of 5 failures cleanly, but a 5th voter (cid 33)
  failed identically across both retry seeds and the run crashed again --
  confirming the measured residual risk was real, not just a small-sample artifact.
- **2026-09-06** (`a5d6b24`) — fix #2: `cast_votes` now falls back to
  `simple_rules.build_ranking` for a single voter rather than raising, at any
  replay budget, with honest provenance tracking (`llm_fallback`). Directly
  implements the plan's own priority order ("must not die mid-run" first).
- **2026-09-06** — Phase 0's baseline re-run (`baseline-2y-p100-vllm-v3`)
  completed cleanly end-to-end: 2266.8s/8 ticks, 632 decisions, 42 replay events
  all recovered, 0 fallback activations. Phase 0 and Phase 0bis both DONE.
  Corrected the flagship cost projection from the Ollama-extrapolated 65-82h down
  to a rough ~35.6h sequential, pending Phase 7's own scale-probe confirmation.
- **2026-09-06** (`5629777`) — Phase 1: re-ran all 3 collapse-flagged decision
  types under vLLM. 2 of 3 still collapse (representative_response,
  coalition_decision); reaction_to_event's SCANDAL branch does not reproduce
  the collapse and its warning is dropped.
- **2026-09-07** — Phase 2: built `run_chunks()`, a shared thread-pool execution
  strategy for the 5 chunked decision types, relaxed `_check_supported()` to
  allow `intra_run_workers > 1` on vLLM, and wrote
  `check_intra_run_concurrency_determinism.py` to prove it. First run of the
  proof found a false FAIL caused by the script's own `run_id` bug (fixed).
  The real result, after the fix: **FAIL, for a genuine reason** — 20/497
  events diverged between workers=1 and workers=8 (all `vote_cast`, all a
  first-attempt success/failure flip with byte-identical resulting ballots),
  confirmed concurrency-specific via a workers=1-vs-workers=1 control (0/497
  diffs). Per the plan's own pre-registered gate, reverted
  `_check_supported()` to its unconditional refusal (now citing both findings)
  and left `run_chunks()` in the codebase as tested, currently-unreachable
  groundwork rather than reverting it outright. The flagship runs sequential;
  Phase 3 (checkpoint/resume) is now the load-bearing mitigation, not a hedge.
- **2026-09-07** — Phase 3: `api/domain/polity/checkpoint.py` (new module),
  `run_simulation(resume=...)`, `run_polity_flagship.py --resume`. Refined the
  original plan after reading the actual code: `graph`/`InstitutionalClock`
  are pure functions of config and are regenerated on resume, never
  snapshotted -- only citizens/parties/pending_rerun/economy_x/
  mobilized_last_tick/the 3 persistent RNG streams are captured. Found and
  fixed a real efficiency bug along the way (`dataclasses.asdict()` on every
  citizen every tick cost the polity test suite +86s; `vars().copy()` is
  303x faster, measured, not assumed). Verified three ways: unit round-trip
  tests, an in-process pytest integration test (injected mid-tick AND
  clean-between-ticks interruptions, both byte-identical to an uninterrupted
  run), and a real `kill -KILL` on a live `run_polity_flagship.py` process
  (tick 52 of 120), resumed via the actual `--resume` CLI flag -- 17,791
  events, zero diffs. 1837 backend tests pass, mypy clean.
