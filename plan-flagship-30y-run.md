# Plan — the flagship run: 30 simulated years at population 500

> **Living document.** Unlike the other `plan-*.md` files here, this one is a
> *tracker*: every phase carries a status line that is updated as the work
> lands, so the state of a multi-day effort survives a lost session. Written in
> English to match the document lineage it continues (`scripts/vllm_*_results.md`,
> `scripts/check_vllm_*_results.md`), not the French of the older plans.
>
> **Status legend**: `TODO` · `IN PROGRESS` · `DONE` · `BLOCKED` · `DROPPED`

**Overall status: Phases 0, 0bis and 5 DONE. Starting Phase 1.**
(last updated 2026-09-06)

| Phase | What | Status |
|---|---|---|
| 0 | Pre-flight: disk, provider switch, baseline timing | **DONE** — real baseline measured, 2266.8s/8 ticks |
| 0bis | **NEW**: `vote_cast` needed a seed override AND a deterministic fallback on vLLM | **DONE** — fixed, confirmed on a clean re-run |
| 1 | Re-test the 3 collapse-flagged decision types under vLLM | TODO |
| 2 | Concurrency unlock + byte-identical determinism proof | TODO |
| 3 | Checkpoint / resume | TODO |
| 4 | Observability (`progress.json`) | TODO |
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
   Ollama-based estimate assumed, though still in "needs Phase 2's concurrency
   unlock to be practical" territory, and still a linear-scaling projection
   from one data point, not a second measurement.
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
`pressure_action`, and pushes the sequential total to roughly **75-82h**. It is
the strongest single argument for Phase 2: without concurrency this run is not
practical.

## Why concurrency is the right lever (and is safe here)

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

## Phase 1 — Re-test the three collapse-flagged decision types under vLLM · TODO

`representative_response` (dt=6), `reaction_to_event` (dt=8, scandal branch) and
`coalition_decision` (dt=9) each carry a `RELIABILITY WARNING` block:
structurally opposite input poles produced byte-identical decisions (4/4, 6/6,
6/6). **All three were measured on Ollama only.** Different weights (AWQ) may
behave differently — the truncation bug already proved backend-specific
behaviour is real.

Reuse the existing collapse-signature scripts, pointed at vLLM:
`check_representative_response_collapse_signature.py`,
`check_coalition_decision_collapse_signature.py`, and the reaction equivalent.

**Decision gate**: if a type still collapses, it stays in the run but every
metric derived from it is labelled `unverified` in the exported artifact, so the
UI cannot present it as trustworthy. If it no longer collapses, record that and
drop the warning.

**Cost**: minutes. Do this before spending days of GPU.

## Phase 2 — Concurrency unlock + determinism proof · TODO

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

## Phase 3 — Checkpoint / resume · TODO

**Change**: per-tick checkpoint so a 3-day run survives interruption.

State to capture at the end of each tick (exhaustive — anything missed silently
corrupts a resume):

- `citizens` (full list, including `chamber_position`, `revealed_position`,
  `pledged_platform`, `event_salience`, `sortition_seat_until_tick`,
  `party_affiliation`, role/office state)
- `parties`, `pending_rerun`, `economy_x`, `graph`, `mobilized_last_tick`
- **All four RNG streams' `bit_generator.state`** (`rupture_rng`, `events_rng`,
  `sortition_rng`, and the graph generator) — a plain reseed is *not* equivalent
  and would diverge
- `tick`, `run_id`, config hash, and the journal's last `event_id`

Write to `runs/<run_id>/checkpoint.json` (atomic: temp file + rename). On resume:
load, **truncate `events.jsonl` to the last event of the last completed tick**,
and continue. The journal is already append-only and flushed per write, so
truncation is well-defined.

Relax the `FileExistsError` guard in the runner to allow explicit `--resume`
while still refusing accidental reuse.

**Gate**: run 4 years uninterrupted; run 4 years killed at tick 8 and resumed;
`events.jsonl` byte-identical between the two.

## Phase 4 — Observability · TODO

**Change**: per-tick progress to stderr and to `runs/<run_id>/progress.json`
(atomic rewrite).

Fields: tick, simulated year, wall-clock elapsed, per-tick duration, rolling ETA,
LLM calls by decision type, replay count, failure count by classification, and
last checkpoint tick.

Cheap and high-value: it turns a 3-day black box into something watchable, and
`progress.json` gives the future UI a live status endpoint for free (§16.1's
"hot regime" without needing the WebSocket yet).

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
| 2 | **`events.jsonl` byte-identical, workers=1 vs workers=8, same seed** |
| 3 | **`events.jsonl` byte-identical, uninterrupted vs killed-and-resumed** |
| 4 | `progress.json` updates per tick; ETA converges |
| 5 | v3 checklist Classes B/C/D measured at pop 500; seats/initial_count decisions recorded |
| 6 | `viz_export.py` output loads; DuckDB queries return expected row counts |
| 7 | 8-year pop-100 parity vs `acceptance_v6b_results.md`; then flagship completes |

Existing gates stay green throughout: `mypy api/` clean, `flake8`, and the polity
test suite (22 files, ~15.4k lines) — especially `test_polity_run_simulation.py`
(188 tests) and `test_polity_llm_behavior_engine.py` (242 tests), which cover the
code Phases 2-3 touch.

## Risks

- **The determinism proof fails.** Mitigation: it is a gate, not an assumption.
  Fallback is sequential + checkpointing (~3 days in resumable segments) — slower
  but still achievable.
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
