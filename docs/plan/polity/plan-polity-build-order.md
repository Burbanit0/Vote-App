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

**Strange behaviour goes to the observation log.** Anything a run does that looks wrong, repeats
when it should vary, or contradicts itself is recorded in `observations.md` with the evidence to see
it again, whether or not a step here addresses it.

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

Settled by S3.5 before `polity` goes to `develop`: none of these findings remain (see its merge).

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
| D1 | Runs are **replayable** from their call log rather than **regenerable** byte-for-byte from their seed | S2.1 | 2026-09-13: replayable from the call log (S0.6 replay is byte-identical); parallel decisions allowed |
| D2 | Population vote: keep LLM `vote_cast` for every citizen, or a deterministic utility vote with the LLM as audit sample (needs an ADR) | S4.1 | 2026-09-13: deterministic utility vote, the LLM voting on an audit sample |
| D3 | Ordinary legislation (ADR-009) before ADR-008 constitutional amendments | S4.2 | 2026-09-13: ordinary legislation first |
| D4 | Adopt non-greedy sampling for thinking calls — only if S1.4 shows it helps | S1.4 adoption | |
| D5 | Launch the p500 batch once Stage 0 is closed, under S0.7's pre-registration | S0.8 | 2026-09-13: launch now, from a worktree at `04358d24` |
| D6 | What should differ between two elections of a run: today nothing the candidacy and nomination decisions read changes, so the same field returns every time (`observations.md` OBS-001–003, OBS-010). Levers: term limits (enforced on both engines since OBS-012's fix), barring or informing about a recalled president, dynamic citizens, sampling above temperature 0 | S4.3 scope | 2026-09-13: four levers -- dynamic citizens (S4.3), a retrospective vote (S4.1), `president_term_limit: 2` by default, and a recalled president barred from the snap election that follows the recall. Sampling stays at temperature 0 |
| D7 | What the sortition chamber deliberates on: today it has no agenda and its prompt tells it to hold still (OBS-004) | S4.2's chamber role | 2026-09-13: the chamber reviews bills, with its suspensive veto (S4.2); its current deliberation calls continue until then |

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
| S0.7 | p500 pre-registration and sweep statistics | — | `feat/polity-p500-preregistration` | `04358d24` |
| S0.8 | p500 batch run and results | S0.1–S0.7, D5 | (run) | |
| S1.1 | Where the time goes, per decision type | S0.5 | (analysis) | |
| S1.2 | Grammar-enforced `vote_cast` invariants | S0.2 | `feat/polity-vote-grammar-invariants` | |
| S1.3 | Thinking-budget A/B | S0.5 | `feat/polity-thinking-budget` | |
| S1.4 | Thinking-mode sampling A/B | S0.5 | `feat/polity-thinking-sampling` | |
| S1.5 | One config validator, one engine switch | S0.2 | `feat/polity-config-validation` | `5f8ad0ff` |
| S2.1 | Replayable concurrency | S0.6, S1.3, D1 | `feat/polity-replayable-concurrency` | |
| S2.2 | Model bake-off harness | S0.5 | `feat/polity-bakeoff-harness` | |
| S2.3 | Minimal model profiles and model override | S0.2 | `feat/polity-model-profiles` | `13150616` |
| S2.4 | First-wave bake-off | S2.2, S2.3 | (run) | |
| S2.5 | Permutation and rendering controls on collapse probes | S2.2 | `feat/polity-probe-controls` | `f3e8ef2c` |
| S3.1 | Typed generic decoder | S0.2 | `feat/polity-generic-decoder` | `98bc0c03` |
| S3.2 | Decision runner for candidacy, reaction, pressure | S3.1, S0.3 | `feat/polity-decision-runner` | `1e2ce8b5` |
| S3.3 | Typed events and event registry | S0.2 | `feat/polity-typed-events` | `7695fafd` |
| S3.4 | Tick state and phase pipeline | S3.3 | `feat/polity-tick-state` | `b27dbea9` |
| S3.5 | Settle the debt ledger | S3.1, S3.2 | `feat/polity-debt-ledger` | `6f85b10a` |
| S4.1 | Utility vote with turnout | D2, S3.4 | `feat/polity-utility-vote` | |
| S4.2 | Policy status quo and ordinary legislation | D3, S3.4 | `feat/polity-legislation` | |
| S4.3 | Dynamic citizens | S3.4 | `feat/polity-dynamic-citizens` | |
| S4.4 | Phase clock | S3.4 | `feat/polity-phase-clock` | `c3a086c1` |
| S5.1 | Run registry | S0.4 | `feat/polity-run-registry` | `2bc3727d` |
| S5.2 | marimo run explorer | S5.1 | `feat/polity-run-explorer` | `f61ec32e` |
| S5.3 | Narratives with checkable claims | S0.5 | `feat/polity-checked-narratives` | `6913a6f9` |
| S5.4 | Generated doc status and wider doc-drift | — | `feat/polity-generated-doc-status` | `e4ac23c6` |

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

*First reading, 2026-09-13* (`scripts/p500_llm_time_results.md`, generated by
`scripts/p500_llm_time_report.py`). It covers seed 1 only and is regenerated with the batch's other
runs.

- **`vote_cast` is 61.2% of model time.** Of its own time, 70.4% is first attempts and 28.9% pays
  for failures: 11.8% retries, 10.7% rejected answers, 6.4% truncations.
- **`chamber_deliberation` is 33.3%.** 39.1% of its time is truncated generations, the runaway
  reasoning S1.3's budget targets.
- **Everything else together is 5.5%.**
- **The unaccounted election-tick time is model time.** Across the four presidential election
  ticks (0, 16, 20, 32), a tick's span outside any model call is 0–1 s. Almost all of an
  election tick is `vote_cast` (2,673–5,197 s of 2,938–5,599 s).

### S1.2 Grammar-enforced `vote_cast` invariants
`blank=1 ⇔ ranking=[]` via `anyOf`/`const`; top-5 via `maxItems`.
**Accepted when:** on the `vote_cast` fixture, the blank-with-ranking validation error
no longer occurs and agreement with `build_ranking` is no lower than baseline. Schema
bytes change: golden updated deliberately.

*Made precise when built, 2026-09-13*:

- **The grammar.** `llm_schemas.vote_cast_json_schema(max_ranking)` makes each ballot `anyOf`
  a blank branch (`blank` const 1, `ranking` maxItems 0) and a ranked one (`blank` const 0,
  `ranking` minItems 1). `maxItems` is set per batch to the rule the validator already
  applies (top five above six candidates, the field size otherwise), so the grammar enforces
  existing rules and adds none. Decision types are now read off a schema's title, which a
  per-batch schema keeps.
- **Checked on the CPU in the server image.** `scripts/check_vote_grammar_xgrammar_results.md`:
  vLLM 0.28.0's xgrammar takes the schema with no backend fallback, and refuses all three
  rejected ballot shapes while accepting the valid ones.
- **Off until accepted.** Production uses it behind `llm.vote_cast_grammar_invariants`
  (`false`), so golden references and every run so far are unchanged. Adoption flips the
  default and updates golden deliberately, as written above.
- **The fixture.** The S2.2 bank's vote cases, `logprob_gate` and `vote_first_choice`. The A/B
  is two bake-off sessions of the control model, one with `--arm vote_grammar`.
- **Accepted when, on those sessions:**
  - the arm's vote_cast validity errors include no "blank=1 requires an empty ranking";
  - its `vote_first_choice` accuracy is at least the baseline's on the same cases, with the
    scorecard's paired McNemar test reported.

### S1.3 Thinking-budget A/B
Arms: no budget, 4096, 2048 for `vote_cast` (chunk 3) and `chamber_deliberation`
(chunk 5), including the known runaway state (`chamber_position == sincere_position`).
First confirm `thinking_token_budget` is honored by the pinned vLLM with ngram
speculation on.
**Pre-registered choice:** the smallest budget whose agreement with `build_ranking` is
within one case of "no budget" on the fixture and whose truncation rate is ≤ 1%.

*Made precise when built, 2026-09-13, before any session:*

- **The precondition.** `scripts/check_thinking_token_budget.py` sends one thinking vote case with
  no budget, 256 and 64. The budget counts as honoured when:
  - each budgeted call's reasoning stays within budget + 16 tokens, the room for the forced end
    string;
  - each budgeted call's answer decodes;
  - the unbudgeted call reasons past 256 tokens.

  vLLM 0.28.0's source takes `thinking_token_budget` on chat completions: it is enabled by the
  `qwen3` reasoning parser the server runs, and the speculative-decoding sampler handles it. Only the
  live check shows it works.
- **The arms.** `thinking_budget_4096` and `thinking_budget_2048` are bake-off request arms. They
  send `thinking_token_budget` on every thinking `vote_cast` and `chamber_deliberation` case. The
  extra field enters the request hash and the call log only when set, so no earlier hash changes.
- **The fixture.** The bank's `vote_first_choice` (14 cases, 40 voters) and `chamber_poles` (10
  cases). Its drift-0 pole is the runaway state, where `chamber_position` equals the sincere
  position.
- **The sessions.** Three on the control model, sharing one server and the same families: no arm,
  and each budget.
- **The readings.**
  - *"Within one case"* means at most one fewer voter agreeing with `build_ranking` on
    `vote_first_choice` than the no-budget session.
  - *The truncation rate* is the share of the arm's vote and chamber calls, rerun pass included,
    ending with finish reason `length`.

### S1.4 Thinking-mode sampling A/B
Temperature 0 against Qwen's recommended thinking settings (temperature 0.6, top-p 0.95,
top-k 20, per-request seeds), same fixtures and metrics.
**Adopt only if** truncations drop with no loss in agreement (D4).

*Made precise when built, 2026-09-13, before any session:*

- **The arm.** `thinking_sampling` is a bake-off request arm. Every thinking `vote_cast` and
  `chamber_deliberation` case gets temperature 0.6, top-p 0.95 and top-k 20, with a seed of its own
  derived from the case id.
- **The fixture.** S1.3's: the bank's `vote_first_choice` and `chamber_poles`.
- **The comparison.** Against S1.3's no-arm session.
- **The readings.**
  - *"Truncations drop"* means the arm's truncation rate, S1.3's measure, is below the no-arm
    session's.
  - *"No loss in agreement"* means at least as many voters agreeing with `build_ranking` on
    `vote_first_choice`.
- **Adoption.** It is D4's, even when both readings hold.

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

*Made precise when built, 2026-09-13*:

- **The mode.** `llm.reproducibility` (strict shipped). Relaxed lifts the one-worker guard on
  vLLM only; Ollama unloads its model between calls. `validate_config` explains the refusal,
  and `run_metadata.json` records the mode and the worker count.
- **Thread safety.** Every piece of client state shared across workers is now thread-safe:
  the replay client is locked; the call log and progress already were.
- **Engine correctness.** A relaxed run with four workers writes the sequential journal byte
  for byte under a deterministic client, and replays to it (tested).
- **The measures** (`concurrency_comparison`):
  - **Agreement:** each arm is replayed from its own call log. The replay's `vote_cast`
    requests carry every voter's distances and blank threshold, so each accepted ballot's
    first choice is scored against `build_ranking`'s rule on those values. Chunks production
    would replace with the deterministic ballot are excluded.
  - **First-attempt failure rate:** first attempts rejected, truncated or failed.
  - **Replayability:** the replay must reproduce the arm's journal.
- **The sweep.** `scripts/run_concurrency_sweep.py run --label <server config>` (GPU, once per
  FP8 KV cache setting), then `compare --label` (no GPU) writes `comparison.md`. The compare
  path was smoke-tested on fake-client arms.

### S2.2 Model bake-off harness
Frozen, content-hashed case bank generated from the existing probes and ground-truth
rules (never copied code). Per model: warm-up, a gate that `think=False` yields zero
reasoning tokens and `think=True` more than zero, the 16-case logprob alignment gate,
the case bank at production shapes, a 10% re-run for the noise floor. Scorecard per
model × decision type: validity, accuracy with Wilson intervals, sensitivity, cost;
paired McNemar and Cochran's Q with Holm correction. Generated JSON and Markdown.
**Accepted when:** on Qwen3-8B-AWQ it reproduces the known numbers — 202/500 declared,
318/500 accurate for candidacy, flat `representative_response`, flat `coalition_decision`.

*Case bank additions from the observation log, 2026-09-13:* party nomination with the
candidate order and cids shuffled, to tell a pick that follows the candidate from one that
follows the listed position (OBS-013); candidacy against the ambition threshold (OBS-011).

*Made precise when built, 2026-09-13* (`bakeoff_cases`, `bakeoff_runner`,
`bakeoff_scorecard`, `bakeoff_statistics`, `bakeoff_report`; scripts `bakeoff_cases.py`,
`run_bakeoff.py`, `bakeoff_report.py`):

- **Case bank.** `scripts/bakeoff/case_bank.jsonl`, ten families (94 cases before S2.5's controls, 174 with them). Each case is
  captured by running a production `decide_*` function against a capturing client, so it
  is the request production sends, not a copy of prompt code. Captured candidacy, vote and
  positioning requests are byte-identical to production's (tested). The generated seed-1
  candidacy requests also match the 20 the live p500 run logged at tick 0.
  - **Shapes.** Cases are rendered at the reference model's production shapes: the
    flagship runner's config (the p500 batch's), vLLM qwen3:8b, seed 42. Every model answers
    the same requests, so comparisons are paired. Only `max_tokens` follows each model's
    profile, by the rule production uses (fixed, prompt-token probe, or profile allowance).
  - **Families.**
    - `logprob_gate`: 16 voters, 8 with a blank sincere ballot.
    - Ground truth: `candidacy_p500` (500 citizens; truth is the ambition threshold);
      `vote_first_choice` (40 voters, 20 blank and 20 ranked; the 300-citizen electorate has
      only 31 blank ballots); `pressure_act` (12 citizens far above their tolerance and 12
      far below, asked one at a time).
    - Contrasts: `response_sweep` (9 points); `coalition_diagonal` (5 points); `reaction_scandal`,
      `chamber_poles` and `positioning_poles` (2 poles each).
    - Permutation: `nomination_permutation` (five p100 populations, each with cids reversed).
  - **Frozen.** A bank changes only on purpose: `bakeoff_cases.py check` verifies the hash and
    reports where production renders differently today, without failing.
- **Per model.** One session of cases, in order:
  - warm-up, with the thinking gate read off its two calls;
  - the logprob gate: all 16 units aligned, or no probability is read anywhere in the session;
  - every case;
  - every tenth case by id, re-run for the noise floor.
  - A session resumes where it stopped. `--replay-calls-from` answers cases from a recorded call
    log without a GPU.
- **Scorecard definitions.**
  - **Validity:** the answer decodes into a batch production accepts.
  - **Accuracy:** an invalid request's units count as wrong.
  - **Sensitivity:** the separation between the poles of the probability read at each level;
    flat is |separation| < 0.10, S2.4's bar. Contrasts with no single-token field (reaction,
    positioning) report whether answers vary, not a separation.
  - **Permutation:** how often the pick names the same citizen, the same listed position, or
    the last one.
- **Deviation from the probes.** The coalition diagonal stops one seat short of a majority. The
  probe's last two points had no shortfall, and production asks nobody then.
- **Acceptance, pre-registered here before any live session.** Read on the Qwen3-8B-AWQ
  control:
  - `candidacy_p500`: 202 of 500 declared and 318 of 500 agreeing with the threshold.
  - `coalition_decision`: flat.
  - `representative_response`: Track B1's shipped reading, since its calibrated prompt shipped
    on 2026-09-11. P(CONCESSION) spreads by less than 0.10 wherever there is pressure (t > 0),
    and is below 0.5 at the one point with none (t = 0). "Flat" in the criterion above is read
    as this.
  - **Open:** the logprob readings need one live GPU session. The candidacy half needs none: the
    p500 batch's seed-42 run sends exactly those requests, so replaying its call log checks it.
    Until then this step has no *Closed by*.

### S2.3 Minimal model profiles and model override
Thinking control per family (`enable_thinking`, `thinking`, `reasoning_effort`, or none),
context limit, chunk sizes and budgets keyed by model rather than by provider; `--model`
on the flagship and sweep runners.
**Accepted when:** Qwen requests are byte-identical (golden unchanged).

*Made precise when built, 2026-09-13:* "keyed by model" means keyed by the served model,
(provider, `llm.model`). The same `qwen3:8b` tag deliberately names Ollama's GGUF and
vLLM's AWQ, and each measurement belongs to one of them. The golden references hash
engine requests, not HTTP bodies, so byte-identity is also checked on the client's
payloads.

### S2.4 First-wave bake-off
Gemma-4-12B QAT W4A16, Granite-4.2-8B NVFP4, Nemotron-3-Nano-4B, Qwen3-4B, Qwen3.5-4B,
with Qwen3-8B-AWQ as control in every session. Each candidate first passes
`check_llm_stack_versions.py --discover` against the pinned image.
**Pre-registered question:** does `coalition_decision`'s collapse (|separation| < 0.10)
persist on at least two non-Qwen families? Every model tested is reported.

### S2.5 Permutation and rendering controls
Permute option codes and orders, renumber citizen ids, and render each case at least
three equivalent ways in the collapse probes.

*Made precise when built, 2026-09-13* (`bakeoff_controls`; the bank is still unanswered, so
the controls join it before it freezes). Every S2.2 contrast case (response, coalition,
reaction, chamber, positioning) gets four controls, each checked to change the surface and
nothing else:

- **Renumbered:** the scenario is captured again through production with every citizen or party
  id reflected, which also reverses the order units are listed in. Each unit records its
  canonical id.
- **Codes:** the answer field's codes (stance, action, or the motif) are cyclically relabelled
  in every table line and every rule that names them, and the option table is re-sorted. Both
  the numbers and the order of options move. The relabelling must invert exactly or no case
  is made. The JSON schema is unchanged because a bijection keeps the set of legal codes.
  Answers are mapped back before production decodes them, and a logprob reading follows its
  meaning to the new code.
- **Two renderings of the user prompt:** indented JSON with keys in reverse order, and one
  `path = value` line per field. Each must parse back to the same values.

The scorecard reports each contrast per control: sensitivity, and agreement with production's
rendering for the same level and the same citizen or party.

**Accepted when:** every base contrast case has all four controls, and every transformation
provably inverts (tested). A collapse is robust when it stays flat under every control; that
is measured in S2.4's sessions, not here.

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

*Made precise when built, 2026-09-13*, in `docs/adr/ADR-011-utility-vote-with-turnout.md`:

- **What was built.**
  - The utility terms, and indifference abstention.
  - The incumbent judged at an election: the holder whose term ends, or the president a rerun
    carries, i.e. the recalled one for a snap election.
  - `vote.mode` (utility shipped), with an LLM audit sample (`vote.audit_fraction` 0.1, journaled
    `audit: 1`, never counted).
- **First acceptance met.**
  - The zero-weight property holds over 400 generated electorates, and the deterministic golden
    reference does not move.
  - Timed: 2.8 ms per 100 ballots against `build_ranking`'s 4.9 ms; an 8-year p100 deterministic
    twin in 0.15 s.
- **Weights ship at zero** (the control arm). The ADR pre-registers the facts a calibrated weight
  set must meet on the p100 deterministic twin: retrospective voting, turnout 50–85%, partisanship,
  and fewer one-president runs (OBS-001). The calibration needs no GPU and is this step's
  remaining work before any weight leaves zero.
- **S2.1's sweep pins `vote.mode: llm`** (`run_polity_flagship.py --vote-mode`): its measure is
  `vote_cast` agreement, which needs the model to cast every ballot.
- **Calibration, 2026-09-13: nothing qualifies, and the weights stay at 0**
  (`scripts/calibrate_utility_vote_results.md`, ADR-011's calibration result).
  - Fact 1 has 0–7 standing incumbents per setting.
  - Fact 4's zero-weight baseline is already 2.2%.
  - The turnout band needs `turnout_cost` ≥ 0.02, while partisanship pushes own-party first
    choices past 90%.
  - A better-powered protocol needs its own pre-registration.

### S4.2 Policy status quo and ordinary legislation (after D3)
ADR-009 first: a policy vector in the issue space; proposer moves it on at most two
dimensions within a step bound; assembly ratification with a coalition majority;
cohabitation block; the sortition chamber's suspensive veto (`veto_power` finally
consumed). Targets named before code: policy congruence, cost of ruling, gridlock under
cohabitation.

*Made precise when built, 2026-09-13*, in `docs/adr/ADR-009-ordinary-legislation.md` (written
before the code, with the targets):

- **The status quo.** Policy is a point in the issue space, starting at the population's
  per-issue median. `Legislature` on `TickState` also keeps the last assembly's seats and
  coalition, the policy at each term's start, and any suspended bill.
- **A bill's path** (`legislation.py`, config section `legislation:`, deterministic on both
  engines).
  - Every `bill_interval_ticks` the president drafts a bill, or, under cohabitation, the
    government's initiating party. It moves policy on the two largest priority-weighted gaps by
    at most `max_bill_step`.
  - Seated parties vote sincerely; it passes with more than half the seats.
  - Under cohabitation the president blocks a bill that moves policy away from them.
  - The chamber reviews the first reading. Under `suspensive_limited` a majority against
    suspends the bill for `veto_delay_ticks`, then it gets a second reading with no second
    review.
  - Six new event types, including a yearly `policy_status` with congruence.
- **Voters judge policy** (`vote.policy_retrospection`, shipped at 0).
  - The judged incumbent, and the governing parties at a legislative election, gain the
    distance policy moved toward each voter during the term: the channel a cost of ruling
    needs.
  - At 0 no ballot or party choice changes (property).
- **First acceptance met.**
  - Each rule and the veto cycle match hand-worked cases.
  - Golden references and the bake-off bank are unchanged, and a disabled run's checkpoints
    gain no keys.
  - A legislating run resumes byte-identical.
- **Ships off.**
  - The ADR pre-registers the targets on the p100 twin over 16 years:
    - L1: checks moderate policy relative to the president.
    - L2: at least one bill enacted per term.
    - L3: gridlock under cohabitation.
    - L4: the cost of ruling.
  - Grid: bill interval, step, and retrospection weight.
  - First smoke run (seeds 1-2): most bills die in a sincerely voting assembly (1 to 5 of 24-29
    enacted over 16 years), so L2 is at risk at the shipped settings. That is what the
    calibration is for.
  - A model-decided proposal or review is a later step with its own pre-registered criterion;
    `chamber_deliberation` keeps running unchanged meanwhile.
- **Calibration, 2026-09-13: nothing qualifies, and legislation stays off**
  (`scripts/calibrate_legislation_results.md`, ADR-009's calibration result).
  - L1, L3 and L4 (from weight 2) hold at all nine settings.
  - L2 fails at all nine: 0.04–0.23 bills per term, with the twin's recall churn (OBS-015)
    multiplying terms.

### S4.3 Dynamic citizens
Pure `update_positions(pop, graph, rng)`: Friedkin–Johnsen with bounded confidence over
the social graph, in the two-factor latent space; anger, anxiety and enthusiasm driving
awakening and mobilization. Step size pre-registered against measured panel stability.
Static population kept as control arm.

*Made precise when built, 2026-09-13*, in `docs/adr/ADR-012-dynamic-citizens.md`:

- **Opinion dynamics** (`opinion_dynamics.py`, config section `dynamics:`).
  - The pure update is `update_latent_factors(factors, anchors, edges, config, rng)`.
  - Friedkin–Johnsen: susceptibility, a step toward the mean of the neighbours within the
    confidence bound, and drift. It runs on the latent factors that `citizen.LatentStructure`
    redraws from the seed, and positions are recomputed from them.
  - One `opinion_dynamics_step` event per tick; a fifth random stream, checkpointed.
- **Emotions** (`emotions.py`, config section `emotions:`).
  - Appraisals: anger and enthusiasm from the gap to the president against the citizen's
    tolerance, anxiety from the economy.
  - Effects: a pull inside the awakening threshold's bounded modulation, and anger lowering the
    pressure rule's tolerance.
  - On the LLM path, the emotions go into `pressure_action`'s context as descriptive signals.
  - One `emotions_updated` event per tick.
- **First acceptance met.**
  - Neutral settings move nobody (property), and a neutral run journals the static run plus the
    two new event types.
  - Golden references and the bake-off bank are unchanged; a static run's checkpoints and snapshots
    gain no keys.
  - A crashed dynamic run resumes byte-identical.
  - Cost: 1.4 ms (update) + 1.6 ms (appraisal) per tick at p500.
- **Both ship off, at neutral settings** (the control arm). The ADR pre-registers the facts and the
  search grid: panel stability 0.70–0.90 over four years, no consensus collapse, neighbour
  homophily, more distinct presidents; discontent mobilizes, anxiety draws people in, honeymoon
  decline. The calibration needs no GPU and is this step's remaining work.
- **Calibration, 2026-09-13: nothing qualifies, and both stay off**
  (`scripts/calibrate_dynamic_citizens_results.md`, ADR-012's calibration result).
  - Dynamics: 0 of 81 settings meet D1–D4. The ten settings passing D1 fail D2 or D4; the static
    arm already elects 5.7 presidents per run.
  - Emotions: E1 and E2 hold even at zero weight. E3 is unmeasurable because no term completes
    (OBS-015).

### S4.4 Phase clock
A phase that is a pure function of the tick, absorbing Track E. Fix Track E's two
documented sharp edges first (`check_staggered_election_live_results.md`). Campaign
windows: 4 ticks before presidential, 2 before legislative elections.

*Made precise when built, 2026-09-13*, in `docs/adr/ADR-010-phase-clock-and-campaign-windows.md`,
which also pre-registers the facts checked:

- **The phase.** `InstitutionalClock.phase(tick)` returns the election held, whether a
  presidential and/or legislative campaign is running, and the ticks to each next election.
- **Window lengths.** `institutions.presidential_campaign_ticks` (4) and
  `legislative_campaign_ticks` (2).
- **Track E inside the campaign.** A staggered election declares on the campaign's first
  tick and nominates on its last.
- **The sharp edges.** Both are fixed at their root: whether a cycle staggered is recorded
  (the declared set is kept until the election consumes it), not inferred from citizen
  roles.

**Accepted when:** the ADR's facts hold in tests and the golden references are unchanged
(every recorded run has staggering off).

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

---

## 9. Execution order for the open steps (set 2026-09-13, 22:20)

What remains open: S0.8 and S1.1–S1.4, S2.1, S2.2 and S2.4 (all needing the GPU in some part), and
the calibrations of S4.1–S4.3 (no GPU). There is one GPU, an RTX 5070 Ti (16 GB). Every
measurement against the server needs the server to itself: concurrent requests change vLLM's
batches, and so its answers. The order below puts the long unattended job first and does the GPU-free work
alongside it.

1. **Resume the p500 batch (S0.8)** from the S0.7 worktree with `--resume-sweep`: seed 1's last
   tick from its checkpoint, then seeds 2 and 42 and the seed-1 repeat, about 21 h. It runs
   detached from any editor (`systemd-run --user`), since OBS-014 lost the first attempt with one.
   Nothing else uses the server until it ends.
2. **Meanwhile, without the GPU:**
   - S1.1's attribution for seed 1, updated with the other runs when they finish.
   - The calibrations of S4.1, S4.3 and S4.2, each by a script that writes its results doc from
     the runs. Each calibration runs on the shipped config with the other two mechanisms off, as
     each ADR states.
   - Then the **combined check**, pre-registered here: every adopted setting on together, same
     twin and seeds, each ADR's facts reported again. A fact that flips is recorded as an
     interaction, and no setting is re-tuned for it.
   - The S1.3 and S1.4 arms, built and tested against a fake client, ready for their sessions.
3. **After the batch, one GPU session at a time**, each on the unchanged `vllm-polity` server
   unless stated:
   1. S0.8's generated summary. S2.2's candidacy acceptance by replaying seed 42's call log.
   2. S2.2's control session (Qwen3-8B-AWQ, no arm): the rest of S2.2's acceptance, and the
      control that S1.2 and S2.4 compare against.
   3. S1.2's `vote_grammar` session; adopted or not by its acceptance.
   4. S1.3: first confirm the pinned server honours `thinking_token_budget` with ngram speculation.
      Then the budget arms.
   5. S1.4's sampling arm. Adoption is D4.
   6. S2.1's sweep, `kv-auto`. Then the same with the server restarted with
      `--kv-cache-dtype fp8`, and the server restored.
4. **S2.4 runs after the queue.** The candidate models download into the vLLM container's Hugging
   Face cache volume. That volume lives under `/var/lib/docker`, a separate 335 GB partition with
   300 GB free. (First written here as blocked on the root filesystem's 6.7 GB free; D8 closed
   for that reason.)

| ID | Decision | Gates | Recorded |
|---|---|---|---|
**How it runs (set 2026-09-13, 22:45).**

- **The batch** runs as the user unit `polity-p500-batch`, started 22:15, from the S0.7 worktree.
- **The seed-1 repeat is excluded (D10).** The batch ends with seed 42, about 15:00 on 2026-09-14.
- **The GPU sessions of step 3** wait in a second unit, `polity-gpu-queue`. It runs
  `Vote-App-gpu-queue/gpu_queue.sh`, from a worktree pinned at `7376c702`, and starts when the batch
  unit ends. Step by step:
  1. S2.2's control session.
  2. S1.2's arm.
  3. S1.3's check, and its two arms only if the budget is honoured.
  4. S1.4's arm.
  5. S2.1's `kv-auto` sweep.

  Each step's start, end and exit code go to `Vote-App-gpu-queue/gpu_queue.log`. The `kv-fp8` sweep
  needs a server restart and is done by hand after.
- **The combined check does not apply:** no calibration adopted a setting (S4.1, S4.3 and S4.2 all
  stay off).

| D8 | Free enough disk for S2.4's five candidate models (about 25–30 GB), and choose what goes | S2.4 | 2026-09-14: not needed. Docker's data, the vLLM model cache included, is on its own partition with 300 GB free |
| D10 | Run the p500 batch without its second seed-1 run | S0.8's red flag 3 | 2026-09-14: excluded. The batch is seeds 1, 2 and 42. The sweep driver was paused during seed 42 and its unit is stopped when seed 42 ends (`Vote-App-gpu-queue/exclude_repeat.sh`). The summary is generated for those three seeds, so flag 3 (same-seed divergence) is not evaluable and is reported as such; S0.7's other two flags stand as pre-registered |
| D9 | The three Stage 4 calibrations ran on a twin whose presidents are recalled after a median of 2 ticks (OBS-015). That churn leaves too few incumbents for S4.1 fact 1 and no full term for S4.3's E3, and it multiplies the terms in S4.2's L2. Nothing qualified. Cause shown: a steady pressure gap above 0.055 walks legitimacy to the recall floor; with the pressure channels off there is no recall. Options: accept the verdicts; or first make the twin's presidency last (pressure weights, the recall floor, or a pressure rule calibrated against the LLM path's), then re-run all three under a new pre-registration | re-calibrating S4.1–S4.3 | |

### S4.1's grid, pre-registered before running (ADR-011 gave the facts, not the grid)

- `partisanship` ∈ {0, 0.05, 0.1}
- `approval` ∈ {0, 0.05, 0.1}, with `approval_party_carryover` 0.5
- `turnout_cost` ∈ {0.005, 0.01, 0.02, 0.04}
- `valence` stays 0, since nothing sources a valence yet.

**Selection.** Among the settings where all four facts hold, the smallest `partisanship +
approval` is adopted. Ties go to the mean turnout closest to 67.5%, the middle of the band. With
nothing qualifying, the weights stay at 0 and the failing facts are reported.

**What is measured.** Facts that the journal does not carry (first choices, the judged incumbent's
record) are recorded by the calibration script. It wraps the production functions and changes
nothing they return.

