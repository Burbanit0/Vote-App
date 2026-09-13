# Polity build order — execution plan

**What this is.** The executable form of the 2026-09-13 research synthesis ("Polity Build
Order": five tracks — simulation model, inference speed, model evaluation, research
tooling, code structure). Every step has a scope, a dependency, a branch, and an
acceptance criterion written *before* the step runs.

**Language.** English, matching `polity-llm-reference.md` and `plan-flagship-30y-run.md`.

---

## 0. How this plan is run

**Reference branch: `polity`.** It is the integration branch for the whole polity
feature. `develop` is merged into `polity` periodically (last sync: `c26e3af4`,
2026-09-13); `polity` goes to `develop` only once the debt ledger below is settled.

**One branch per step.** `feat/polity-<step>` (or `fix/`, `docs/`) cut from `polity`,
merged back with `--no-ff`, pushed. Never commit a step directly on `polity`.

**Gates before every merge into `polity`** (run from `fast_api_voter/`):

```bash
.venv/bin/python -m mypy api/ --config-file mypy.ini   # strict, must stay clean
.venv/bin/ruff check .                                  # CI lints scripts/ too
.venv/bin/lint-imports                                  # routes -> domain -> engine
.venv/bin/python -m pytest api/tests -n auto -q         # full backend, CI's coverage gate
                                                        # (not -o addopts="": that drops the
                                                        # benchmark ignore, and benchmarks
                                                        # fail under xdist)
../scripts/check_quality_ratchet.sh                     # no increase (see voter-ci skill)
```

plus the step's own acceptance criterion. Frontend gates only when `voter-app/` changes.

**Evidence rule — this file must not go stale.** A step's *Closed by* cell holds exactly
one thing: the merge commit that closed it, or nothing. No prose status, no counters.
Everything else lives in that merge's commit messages and in results docs. (The synthesis
found five plan docs contradicting their own sections because status was hand-maintained.)

**Pre-registration.** Measurement steps state their criterion here before running; a
criterion changed after seeing data is recorded as changed, with the reason.

**Golden references guard refactors.** Once S0.2 lands, any change to prompt bytes or
journal bytes must be an intentional golden update in the same commit, explained in its
message.

### Debt ledger versus `develop`

Measured at `c26e3af4` with CI's exact commands. Polity adds, relative to develop's
CI-validated baseline:

- **radon C+ (+8):** `llm_behavior_engine._complete_and_decode_with_replay`,
  `decide_coalition`, `decide_party_nominations`, `_run_coalition_negotiation`,
  `build_pressure_user_prompt_toon` (unused outside scripts); `llm_client._extract_content_and_logprobs`;
  `run_digest.build_digest`, `population_impact_by_year`;
  `run_polity_simulation._nominate_and_position_llm`.
- **jscpd (+5):** `llm_client.py` duplicated vLLM request bodies (~675-693, ~920-936);
  `llm_behavior_engine.py` prompt-builder fragments (~3324-3345, ~3405-3420).

Settled by S3.5 before `polity` goes to `develop`.

### Already closed before this plan

| Work | Closed by |
|---|---|
| Pre-p500 hardening: staggered-election nominee fix, fallback verdict, `--staggered-election`, version-pin decision, model discovery | `7ef06316` |
| Sync `develop` into `polity`, quality baseline re-measured with debt ledger | `c26e3af4` |

---

## 1. Decisions that gate steps

Only the project owner makes these. A gated step does not start until its decision is
recorded here, with the date.

| ID | Decision | Gates | Recorded |
|---|---|---|---|
| D1 | Runs are **replayable** from their call log rather than **regenerable** byte-for-byte from their seed | S2.1 | |
| D2 | Population vote: keep LLM `vote_cast` for every citizen, or a deterministic utility vote with the LLM as audit sample (needs an ADR) | S4.1 | |
| D3 | Ordinary legislation (ADR-009) before ADR-008 constitutional amendments | S4.2 | |
| D4 | Adopt non-greedy sampling for thinking calls — only if S1.4 shows it helps | S1.4 adoption | |
| D5 | Launch the p500 batch once Stage 0 is closed, under S0.7's pre-registration | S0.8 | |

---

## 2. Steps

| Step | What | Depends | Branch | Closed by |
|---|---|---|---|---|
| S0.1 | Housekeeping from the synthesis | — | `fix/polity-synthesis-housekeeping` | `904f5523` |
| S0.2 | Golden references for prompts and journals | — | `feat/polity-golden-references` | `2b4290fd` |
| S0.3 | Retry provenance for all nine decision types | S0.2 | `feat/polity-retry-provenance` | `3593e65b` |
| S0.4 | Complete run provenance | — | `feat/polity-run-provenance` | `22a12676` |
| S0.5 | Per-call LLM log and time attribution | S0.2 | `feat/polity-llm-call-log` | `bad1961c` |
| S0.6 | Replay client | S0.5 | `feat/polity-replay-client` | `8aefd0d3` |
| S0.7 | p500 pre-registration and sweep statistics | — | `feat/polity-p500-preregistration` | |
| S0.8 | p500 batch run and results | S0.1–S0.7, D5 | (run) | |
| S1.1 | Where the time goes, per decision type | S0.5 | (analysis) | |
| S1.2 | Grammar-enforced `vote_cast` invariants | S0.2 | `feat/polity-vote-grammar-invariants` | |
| S1.3 | Thinking-budget A/B | S0.5 | `feat/polity-thinking-budget` | |
| S1.4 | Thinking-mode sampling A/B | S0.5 | `feat/polity-thinking-sampling` | |
| S1.5 | One config validator, one engine switch | S0.2 | `feat/polity-config-validation` | |
| S2.1 | Replayable concurrency | S0.6, S1.3, D1 | `feat/polity-replayable-concurrency` | |
| S2.2 | Model bake-off harness | S0.5 | `feat/polity-bakeoff-harness` | |
| S2.3 | Minimal model profiles and model override | S0.2 | `feat/polity-model-profiles` | |
| S2.4 | First-wave bake-off | S2.2, S2.3 | (run) | |
| S2.5 | Permutation and rendering controls on collapse probes | S2.2 | `feat/polity-probe-controls` | |
| S3.1 | Typed generic decoder | S0.2 | `feat/polity-generic-decoder` | |
| S3.2 | Decision runner for candidacy, reaction, pressure | S3.1, S0.3 | `feat/polity-decision-runner` | |
| S3.3 | Typed events and event registry | S0.2 | `feat/polity-typed-events` | |
| S3.4 | Tick state and phase pipeline | S3.3 | `feat/polity-tick-state` | |
| S3.5 | Settle the debt ledger | S3.1, S3.2 | `feat/polity-debt-ledger` | |
| S4.1 | Utility vote with turnout | D2, S3.4 | `feat/polity-utility-vote` | |
| S4.2 | Policy status quo and ordinary legislation | D3, S3.4 | `feat/polity-legislation` | |
| S4.3 | Dynamic citizens | S3.4 | `feat/polity-dynamic-citizens` | |
| S4.4 | Phase clock | S3.4 | `feat/polity-phase-clock` | |
| S5.1 | Run registry | S0.4 | `feat/polity-run-registry` | |
| S5.2 | marimo run explorer | S5.1 | `feat/polity-run-explorer` | |
| S5.3 | Narratives with checkable claims | S0.5 | `feat/polity-checked-narratives` | |
| S5.4 | Generated doc status and wider doc-drift | — | `feat/polity-generated-doc-status` | |

---

## 3. Stage 0 — before the p500 batch

### S0.1 Housekeeping from the synthesis
- Correct the overclaim in `scripts/run_polity_seed_sweep_p100_results.md` and in
  `plan-distribution-positions-seeds.md` §4.1: the p100 sweep does not *settle*
  representativeness. Recomputed: 95% BCa interval for mean `office_occupancy`
  0.888–0.955 (first recorded as 0.894, a 10,000-resample figure on rounded values; see
  S0.7); 95% prediction interval for one new seed 0.81–1.05 (past the ceiling);
  "alert on 2 of 10 seeds" 2.5–55.6% (Clopper–Pearson); 8 of 10 seeds within ±0.05.
- Remove the unused `sorted_candidates` import (ruff F401) in
  `scripts/check_party_nomination_position_logprobs.py`.
- SessionStart hook (`.claude/hooks/notify_run_digest.py`): look in every `*_runs`
  directory, not only `flagship_runs`.

**Accepted when:** `ruff check .` is clean; the hook lists the ten `sweep-8y-p100-*`
runs when run against the repo.

### S0.2 Golden references
- A recording fake LLM client that captures every `(system, user, schema)` request.
- A committed manifest of sha256 hashes: every captured request, plus `events.jsonl`, for
  (a) a deterministic 2-year population-40 run and (b) a fake-LLM 2-year population-40 run.
  (Planned at population 30; candidacy chunking refuses batches under 20 citizens, so 30
  cannot run with the LLM enabled.)
- `scripts/gen_polity_golden.py` regenerates it; a pytest compares, failing with a
  "regenerate only if intentional" message.

**Accepted when:** the test passes on `polity`, and changing one prompt byte makes it
fail (verified true negative, then reverted).

### S0.3 Retry provenance for all nine decision types
All nine types retry with varied sampling; only `vote_cast` and `chamber_deliberation`
journal `retry_sampling_varied`, so digests undercount retries for the other seven.

**Accepted when:** a fake client that fails the first attempt of one call per type
produces a journaled retry for all nine, and `progress.json`'s retry count equals the
number of decisions those recovering retries produced. A retry that decodes but then
fails validation journals as a fallback, not a retry. Golden updated deliberately in the
same commit.

*Criterion changed before running, 2026-09-13:* it first said the retry count equals
"the number of injected failures". `progress.json` counts decisions carrying the flag,
not calls, and one failed call retries a whole chunk (3 voters, 20 candidacy citizens),
so that count was never the right target. The validation clause was added after reading
the vote and chamber paths: they flagged fallback decisions as retries.

### S0.4 Complete run provenance
`run_metadata.json` gains: git SHA and dirty flag, vLLM image tag, served model repo and
revision, a sha256 of the prompt-builder source, seed, and run shape (years, population,
seats, engine, override flags). First check `origin/feat/polity-live-ui` (`5d713eff`) for
reusable run-shape and config-digest work.

**Accepted when:** a 1-year population-30 deterministic run writes every field, with
LLM-only fields explicitly `null` and the engine recorded as `deterministic`.

### S0.5 Per-call LLM log and time attribution
- `llm_calls.jsonl` beside `events.jsonl`, one line per HTTP call: `call_id`,
  decision type, tick, unit ids, attempt, seed, temperature, `max_tokens`, request
  hash, prompt / completion / reasoning / cached tokens, latency, `finish_reason`,
  reasoning text, content. LLM-derived events gain `llm_call_id`.
- Thread-safe writer; never fails a run (same contract as `run_digest`).
- `scripts/attribute_llm_time.py`: seconds and tokens per decision type, split into
  first attempt, retry, truncation, and budget probe.

**Accepted when:**
1. On a fake-client run, every LLM-derived event's `llm_call_id` resolves to a logged call.
2. The golden journal changes only by the added `llm_call_id` field.
3. On a live 2-year population-100 run against vLLM, the writer's own timers show
   ≤ 5 ms per call, file size is recorded, and attributed LLM time accounts for
   ≥ 90% of the run's wall-clock.

### S0.6 Replay client
An LLM client that serves responses from a run's `llm_calls.jsonl` by request hash and
fails loudly on any unrecorded request.

**Accepted when:** replaying the S0.5 live run reproduces its `events.jsonl`
byte-for-byte without contacting the server.

### S0.7 p500 pre-registration and sweep statistics
- Sweep summaries gain bootstrap (BCa) intervals, Clopper–Pearson intervals for rates,
  and a prediction interval for one new seed; the driver supports repeating a seed.
- Design: seeds 1, 2 and 42 at 8 years / population 500 / 75 seats, plus a second run of
  seed 1 to measure inference noise at a fixed seed.
- Pre-registered reading, written before launch: n = 3 seeds cannot establish
  equivalence with the p100 leg and will not be reported as doing so. **Red flags:** any
  seed with `office_occupancy` < 0.70 (the project's existing occupancy bar); any
  decision type above the 10% fallback alert, `party_nomination_choice` included;
  divergence between the two seed-1 runs larger than the spread across seeds.

**Accepted when:** the criterion is committed before the first p500 run starts.

*Made precise before launch, 2026-09-13*
(`fast_api_voter/scripts/run_polity_seed_sweep_p500_preregistration.md`):
- Flag 3 is measured on `office_occupancy`.
- Flag 2 reads exact per-type counts from `progress.json`.
- The batch runs single-tick elections, like the p100 leg.
- The batch runs from a dedicated worktree at the S0.7 merge. The generated summary
  checks every run's S0.4 provenance, and a mixed batch is not read against the flags.
- The p100 BCa interval recorded under S0.1 is corrected to 0.888–0.955 (see S0.1).

### S0.8 p500 batch run and results
Runs under S0.4 and S0.5, so every p500 run carries full provenance and a call log.
The results doc is generated by the sweep summary, not written by hand, and read against
S0.7 only.

---

## 4. Stage 1 — stop paying for failures

### S1.1 Where the time goes
`attribute_llm_time.py` over the p500 call logs: per decision type, share of wall-clock
in first attempts, retries, truncations and probes, and the election-tick breakdown the
current data cannot explain (~3,800 s of an election tick unaccounted for).

### S1.2 Grammar-enforced `vote_cast` invariants
`blank=1 ⇔ ranking=[]` via `anyOf`/`const`; top-5 via `maxItems`.
**Accepted when:** on the `vote_cast` fixture, the blank-with-ranking validation error
no longer occurs and agreement with `build_ranking` is no lower than baseline. Schema
bytes change: golden updated deliberately.

### S1.3 Thinking-budget A/B
Arms: no budget, 4096, 2048 for `vote_cast` (chunk 3) and `chamber_deliberation`
(chunk 5), including the known runaway state (`chamber_position == sincere_position`).
First confirm `thinking_token_budget` is honored by the pinned vLLM with ngram
speculation on.
**Pre-registered choice:** the smallest budget whose agreement with `build_ranking` is
within one case of "no budget" on the fixture and whose truncation rate is ≤ 1%.

### S1.4 Thinking-mode sampling A/B
Temperature 0 against Qwen's recommended thinking settings (temperature 0.6, top-p 0.95,
top-k 20, per-request seeds), same fixtures and metrics.
**Adopt only if** truncations drop with no loss in agreement (D4).

### S1.5 One config validator, one engine switch
One `validate_config()` called from `load_config` and at `run_simulation` start;
`_assert_coherent` removed; deterministic-vs-LLM resolved once instead of at nine
`config.llm.enabled` sites.
**Accepted when:** golden unchanged; any test found building an incoherent config is
fixed, not silenced.

---

## 5. Stage 2 — faster runs, fair comparisons

### S2.1 Replayable concurrency (after D1)
`llm.reproducibility: strict | relaxed`, recorded in run metadata. Relaxed allows
workers > 1 within a decision type; client state made thread-safe.
Sweep at 1 year / population 100: workers 1, 4, 8, 12 × FP8 KV cache on/off.
**Pre-registered comparison against workers = 1:** `vote_cast` agreement with
`build_ranking` within ±2 points; first-attempt failure rate within ±5 points; wall-clock
speedup reported whatever it is. Each run replayable through S0.6.

### S2.2 Model bake-off harness
Frozen, content-hashed case bank generated from the existing probes and ground-truth
rules (never copied code). Per model: warm-up, a gate that `think=False` yields zero
reasoning tokens and `think=True` more than zero, the 16-case logprob alignment gate,
the case bank at production shapes, a 10% re-run for the noise floor. Scorecard per
model × decision type: validity, accuracy with Wilson intervals, sensitivity, cost;
paired McNemar and Cochran's Q with Holm correction. Generated JSON and Markdown.
**Accepted when:** on Qwen3-8B-AWQ it reproduces the known numbers — 202/500 declared,
318/500 accurate for candidacy, flat `representative_response`, flat `coalition_decision`.

### S2.3 Minimal model profiles and model override
Thinking control per family (`enable_thinking`, `thinking`, `reasoning_effort`, or none),
context limit, chunk sizes and budgets keyed by model rather than by provider; `--model`
on the flagship and sweep runners.
**Accepted when:** Qwen requests are byte-identical (golden unchanged).

### S2.4 First-wave bake-off
Gemma-4-12B QAT W4A16, Granite-4.2-8B NVFP4, Nemotron-3-Nano-4B, Qwen3-4B, Qwen3.5-4B,
with Qwen3-8B-AWQ as control in every session. Each candidate first passes
`check_llm_stack_versions.py --discover` against the pinned image.
**Pre-registered question:** does `coalition_decision`'s collapse (|separation| < 0.10)
persist on at least two non-Qwen families? Every model tested is reported.

### S2.5 Permutation and rendering controls
Permute option codes and orders, renumber citizen ids, and render each case at least
three equivalent ways in the collapse probes.

---

## 6. Stage 3 — structure

### S3.1 Typed generic decoder
Replace the nine `decode_*_batch` functions with one typed generic taking named extractor
functions (prototype passed strict mypy). Same public names. **Golden unchanged.**

### S3.2 Decision runner
`DecisionSpec` plus one runner owning chunking, replay, fallback and provenance; move
candidacy, reaction and pressure first, keeping `decide_*` signatures as thin wrappers.
**Golden unchanged.**

### S3.3 Typed events and registry
One frozen type per event keeping today's payload keys; `ALL_EVENT_TYPES` and the
indexer and viz event sets derived from one registry. Every line of the golden journal
validates. **Golden unchanged.**

### S3.4 Tick state and phase pipeline
A `TickState` the checkpoint serializes whole; phases as an ordered list; phase function
names kept or crash tests moved to a phase hook. **Golden unchanged.**

### S3.5 Settle the debt ledger
Bring radon C+ and jscpd back to develop's baseline, or justify each remaining finding
at its source; then run `check_quality_ratchet.sh --update` on a branch fresh from
`develop`-synced `polity`.

---

## 7. Stage 4 — a world that changes

Each step starts with an ADR that pre-registers its target stylized facts, and keeps
today's model as a control arm.

### S4.1 Utility vote with turnout (after D2)
`utility_ballot()` beside `build_ranking` with partisanship, retrospective approval,
valence and turnout terms. **First accepted when** every new term at zero reproduces
`build_ranking` exactly (Hypothesis property test); then timed on the p100 deterministic
twin.

### S4.2 Policy status quo and ordinary legislation (after D3)
ADR-009 first: a policy vector in the issue space; proposer moves it on at most two
dimensions within a step bound; assembly ratification with a coalition majority;
cohabitation block; the sortition chamber's suspensive veto (`veto_power` finally
consumed). Targets named before code: policy congruence, cost of ruling, gridlock under
cohabitation.

### S4.3 Dynamic citizens
Pure `update_positions(pop, graph, rng)`: Friedkin–Johnsen with bounded confidence over
the social graph, in the two-factor latent space; anger, anxiety and enthusiasm driving
awakening and mobilization. Step size pre-registered against measured panel stability.
Static population kept as control arm.

### S4.4 Phase clock
A phase that is a pure function of the tick, absorbing Track E. Fix Track E's two
documented sharp edges first (`check_staggered_election_live_results.md`). Campaign
windows: 4 ticks before presidential, 2 before legislative elections.

---

## 8. Stage 5 — runs you can explore, stories you can trust

Can proceed alongside Stages 1–4.

- **S5.1 Run registry:** one DuckDB query over every `*_runs` directory, tolerant of the
  three run-format generations.
- **S5.2 marimo run explorer:** tick slider, term timeline, citizen biographies,
  cross-seed panels.
- **S5.3 Narratives with checkable claims:** `event_id` on timeline entries, anchors in
  TIMELINE.md, a mechanical claim checker; story skeletons clustered across seeds.
- **S5.4 Generated doc status:** cog blocks with `cog --check` in CI; the doc-drift agent
  widened to `docs/plan/polity`.
