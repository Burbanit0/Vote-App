# Polity: where it stands, and the plan to February 2027

> **status:** live — the page to read first for Polity: the assessment of 2026-11-15 and the staged plan that follows from it; Stage 0 (this page, the status lines, EXP-026) is this PR, Stages 1 to 5 each start on the owner's go. (Set 2026-11-15; `docs/README.md` lists every plan.)

**What this is.** A full review of Polity made on 2026-11-15 at the owner's request: what is solid,
what is weak, and what to do over the next two to three months. It is written for the owner, as the
single page that says where Polity stands. It does not replace
[`plan-scenarios-v1.md`](plan-scenarios-v1.md), which still says *what to build and under which
gate*; it says *in which order, with which compute, and what to stop reading*.

**Which document governs what** (four Polity plans were "live", three of them roadmaps with no stated precedence):

| Question | Document |
|---|---|
| Where does Polity stand, what is next? | this page |
| What is a scenario, the divergence test, the step table | [`plan-scenarios-v1.md`](plan-scenarios-v1.md) (live) |
| How to rent a GPU and what the 27B probes found | [`plan-rented-gpu-runs.md`](plan-rented-gpu-runs.md) (live) |
| Why the agents, the constitution, the forum and the parties exist | [`plan-polity-agency-roadmap.md`](plan-polity-agency-roadmap.md) (superseded: a record) |
| The 2026-09-13 execution steps | [`plan-polity-build-order.md`](plan-polity-build-order.md) (superseded: a record) |
| Strange behaviour seen in runs | [`observations.md`](observations.md) |

**Decisions taken with the owner (2026-11-15).** Polity stays **the owner's research instrument**
(scenarios and typology), not a showcase and not a new study. The three things that hurt most are:
runs look alike, the model is fragile, and the project is hard to keep track of. Compute is the
local 16 GB card plus **about $50** of rented GPU over the period. Clean-up is **medium**: no split
of the two large files. Publication: **finish what exists** (the drafted preprint, the Zenodo
upload), no new study. The horizon is two to three months.

---

## 1. The picture in one paragraph

Polity is a carefully built engine whose behaviour code last changed on **2026-10-25** (#1001,
ADR-040). The direction set on 2026-10-21, "a world, not an instrument" (measure variety, decide the
crowd by rule, keep the model for the leaders), was then built almost entirely **without the
model**: the catalogue of 1,000 runs and its four archetypes are rule-only, and the scenario profile
has **never been run with the model playing the leaders**. The condition the owner attached to that
direction on 2026-10-21 (that a rule-based crowd improves speed and reliability; the scenarios plan
records only its open "optimistic 2×" claim) and its central bet (the model adds
something where it plays leaders) are both unmeasured. That measurement is the hinge of this plan.

## 2. What is good

- **Reproducibility is designed in.** A config hash is checked on resume; the commit, the prompt
  hash, the vLLM image and the model revision are stamped beside the journal
  (`run_provenance.py`); every model call is logged and a run replays from that log, byte-identical
  at full scale in 86 s (EXP-020). A committed golden holds every prompt and event.
- **Model failures degrade to rules, and are counted.** Each decision type has a rule fallback,
  every event carries `llm_fallback`, and the digest and the sweep summary alert above 10% per type.
  The nine decoders are fuzzed in CI.
- **Negative results are written down.** 54 observations, 40 ADRs, pre-registered gates; rewiring
  (ADR-036), the "logical" field order (EXP-025), vLLM 0.32.0 and now 0.33.0 (EXP-026) were all
  rejected on a measurement, and a two-minute probe is what caught 0.33.0.
- **A cheap run path exists.** The rule-only twin runs a seed in 1.3 s and 1,000 runs in 8 minutes.
- **The scenario tooling is built.** Trajectory metrics, block-wise archetypes, the divergence
  test, and the catalogue with PRIM boxes (`catalogue.py`, `run_polity_catalogue.py`).
- **Institutions have been varied, on the rule path.** The catalogue's hypercube covers the voting
  method, the threshold and the seat rule among twelve dimensions, and its boxes name them
  (alternation with IRV, Borda, Copeland or Schulze under D'Hondt; realignment with plurality or
  two-round; stasis with largest remainder): `fast_api_voter/scripts/run_polity_catalogue_results.md`.
- **Boundaries are clean.** One adapter to the voting engine (`ballot_and_aggregation.py`), a
  read-only explorer confined to its root, a typed frontend on generated OpenAPI types.
- **The test suite is large.** 95 `test_polity_*` files and about 2,400 tests; 146 of them are
  about byte-identity, replay or resume. The config loader is typed and refuses what it does not know.

## 3. Weak points

1. **The model arm is missing.** Counted ballots come from the kernel (ADR-011), the scenario
   profile turns the model crowd off, and no scenario-profile run with model leaders exists. Four
   items of `plan-scenarios-v1.md` §5 wait on a model run that was never made: step 2's timing, the
   catalogue's GPU stage, ADR-031 option B, and step 7's classification of the LLM president.
2. **Runs look alike where the model runs.** Every *model* run on record uses the same institutions
   (two-round, D'Hondt, a 5% threshold). The one informal reading of the divergence test on the model
   path (phase15, five seeds) had no run inside the plausibility band. On the rule path variety
   exists (alternation 59%, churn 16%, stasis 13%, realignment 12% in sweep 5), but with **one run
   per point**: a box mixes a setting's effect with seed noise, and a negative control once appeared
   in a box. Only about a third of the runs pass all four plausibility checks at once (342 of 1,000
   in sweep 4, 308 in sweep 5); the owner stopped calibrating there on 2026-10-24.
3. **The model is fragile where it classifies.** `representative_response` and `coalition_decision`
   ignore their input (OBS-007; 299 of 304 real answers are the same). The 8B's audit vote is wrong
   60% of the time at the 2,048 thinking budget and 12% at 8,192, verdict unresolved (OBS-054). The
   thinking budget binds on most leader calls. **Agent turns have no accuracy check at all**: the
   bake-off bank has no ground-truth family for them. vLLM 0.32.0 and 0.33.0 both break
   `representative_response` through compact JSON, with no setting to turn it off (EXP-025, EXP-026).
4. **The evidence is thin and spread over commits.** Phase 4's exit rests on one ensemble with one
   seed of margin (4 of 10 against a bar of 3). Phases 12 to 16 are five seeds each on four commits.
   The founding lock rests on one seed pair; 27B against 8B on one seed each. ADR-030's ten-seed
   sign-flip gate was never run. The exits of Phases 1 to 3 were never assessed. The three 30-year
   runs, the explorer export and the preprint's data predate every agency mechanism.
5. **It is hard to keep track.** Before this page, no Polity document recorded anything after
   2026-10-25 and the journal stopped at 2026-10-12. Three roadmaps were "live" with no precedence,
   two with status lines that contradicted their own body. On the machine: 28 worktrees, 127 local
   branches, 46 run folders, 148 run digests of which three have a written story.
6. **Code debt, bounded.** Two large files (`llm_behavior_engine.py`, 5,499 lines, where six of the
   nine decision types carry their own chunk, retry and fallback loop; `run_polity_simulation.py`,
   3,581 lines). Config keys that nothing reads: nine checked for this page, about two dozen by the
   survey's count. The scenario presets live in a launcher script
   (`fast_api_voter/scripts/run_polity_flagship.py`) that about 26 other scripts and 7 test files name. Four
   prompt builders with no production caller. About 36 scripts that nothing references. About
   4,200 lines of research code (bake-off, calibration, statistics) inside the domain package.

**Verdict.** The engineering is ahead of the science. The period should produce **one answer** (does
the model, playing the leaders, add variety worth its cost?) and **one confirmed map** (which
institutions lead to which trajectories), on a project one page can describe.

## 4. The plan

Rules for the whole period, all of them the owner's already: no new mechanism or ADR without a
diversity measurement; runs are compared to each other, never to a control arm; an ensemble is ten
seeds on one commit; every stage ends by updating this page; every GPU step, local or rented, is
asked for first.

| Stage | Weeks | What | Compute |
|---|---|---|---|
| 0 | 1 | This page, the status lines, EXP-026 | none |
| 1 | 2-3 | Medium clean-up, no behaviour change | none |
| 2 | 3-6 | The model as leaders: timing, ten seeds, gate G2 | local GPU |
| 3 | 5-8 | A leader tier that can be trusted | local GPU, one rented session |
| 4 | 7-11 | The institutional map confirmed, then the model on its cells | CPU, then local GPU |
| 5 | 10-12 | Publication checklist, a reference run, this page updated | optional local GPU |

### Stage 0. One page that says where Polity stands

This PR: this page; the status lines of the agency roadmap, the build order and the scenarios plan;
the Polity row and next steps of `docs/STATUS.md`; ADR-031 in the ADR index and ADR-001's status;
EXP-026 for vLLM 0.33.0; a journal entry.

### Stage 1. Medium clean-up, no behaviour change

Small PRs, each with the golden byte-identical.

- **Done (PR "drop nine config keys nothing reads", no behaviour change: 150 of 150 rule-only catalogue
  points identical to the base, and the fixture's journal byte-identical).** Remove the config keys
  nothing reads, in `polity_config.yaml` and `config.py`. Nine have no reader
  outside the loader (checked 2026-11-15): `llm.cache_backend`, `llm.cache_url`,
  `llm.personas_count`, `parallel.runs_in_parallel`, `metrics.compute_every_ticks`,
  `journal.snapshot_every_ticks`, `journal.log_non_events`, `legitimacy.recall_cooldown_ticks` and
  `institutions.assembly_term_limit`. Two need a decision, not a deletion:
  `candidacy.max_candidates_hard_cap` is read by one live script
  (`check_polity_scale_gate_pop500.py`, which itself reports it as dead for the simulation), and
  `journal.format` accepts `parquet` in the loader only for compaction to refuse it. The survey
  counted about two dozen unread keys; the rest are found and checked the same way before anything
  goes. The explorer fixture's manifest is regenerated (config hash only, as in #982).
- Move the flagship, exploration and scenario presets from `fast_api_voter/scripts/run_polity_flagship.py` into the
  domain package; the scripts and tests import them from there.
- Archive the four caller-less prompt builders and the unreferenced scripts under
  `fast_api_voter/scripts/archive/` (their results notes stay where they are). One constant for the fallback alert.
- Refresh `polity-llm-reference.md` (verified at a commit of 2026-09-11) and `fit-for-inference.md`
  (it predates OBS-050 to OBS-054).
- Remove the worktrees and branches whose PR is merged. `Vote-App-monitor` is kept.
- **Left out on purpose:** splitting the two large files, one shared loop for the nine decisions.

### Stage 2. The missing measurement: the model as leaders

- **2a. Timing probe.** `--profile scenario` with the model playing the agents, 8 years, 100
  citizens, one seed, alone on the GPU: wall clock, calls, fallbacks and budget binding per agent
  decision. It settles the condition of 2026-10-21.
  **Done 2026-11-16 (EXP-027):** 35.8 min and 609 model calls, 0 fallbacks, on one seed; faster than the
  exploration profile for design reasons, and the run fails three plausibility measures (`enp_seats`, `turnout`,
  `volatility`, archetype `fragmentation`). Variety is 2b's question.
- **2b. Ten seeds on one commit.** The divergence test read on the model path, and each run placed
  on the rule catalogue's archetype map: does the model reach regions the 1,000 rule runs do not?
  **Done 2026-11-17 (EXP-028):** ten seeds, 0 fallbacks, 5 h 14 min of GPU. Five archetypes against the rule twin's two on the
  same seeds, and every run above the catalogue's range of effective parties, but the runs' spread over time is only about
  8% larger than the twin's, 9 of 10 fail the plausibility band (twin: 3), and the difference sits in the 45 to 54 parties
  founded per run (twin: none).
- **2c. On the same runs:** step 7's classification of the LLM president against the four leader
  rules. ADR-031 option B is **not** part of this stage: it is not built, and its pre-registered
  test is a control against a candidate on ten paired seeds of the exploration profile, which is
  both a new mechanism and a control arm. Whether to build it and how to test it is 4c's decision.
  **Done 2026-11-17 (EXP-029):** none of the four rules fits the model's leaders: they move toward the public median the
  prompt shows (99% of the nominees' shifted dimensions, 76% of the presidents'), with no pull toward their party, presidents reverse
  their previous move more often than they repeat it, and the steps are several times a rule's; read from their own shifts, since no
  rule moves anything in these runs.
  **Founding read 2026-11-17 (EXP-030, CPU on the call log and the logged prompts):** the model answers `found` on 80% of the turns where
  its prompt says founding is allowed, 10% below the bar and 0.4% when the party is locked; the kernel accepts 492 of 832. The 45 to 54
  foundings follow the prompt's stated rule on a bar of 5 citizens at p100 and the mechanism being on in the model arm only; that suggests they
  are not evidence that the model's judgement adds a party system, but a clear response is neither "no response" nor "inconclusive", and a rule
  "found at about 0.8 when allowed" was not built or run at that point.
  **Rule run 2026-11-17 (EXP-031, CPU, 50 s):** that rule reproduces the model arm's party system (45 to 56 founded, effective parties median 7.7
  against 8.1, no run inside the band) but not its label spread (churn 6 of 10, entropy 1.30 against 2.25); the leaders and amendments are not
  separated from the rest. The G2 question narrows to whether the model's leaders and amendments add variety a rule does not.
- **Gate G2, the owner's call on the numbers.** If model leaders add variety at an acceptable cost,
  Stages 3 and 4 run as written. If they do not, the instrument is the rule engine and its
  catalogue, the model becomes an optional narrator and limit-tester, Stage 3 shrinks to 3d, and
  this page says so.

### Stage 3. A leader tier that can be trusted

- **3a.** A ground-truth case family for agent turns in the bake-off bank, about 30 to 40 cases.
- **3b.** The thinking budget for leaders: OBS-054's replay again, **serial** this time. It already
  ran at temperature 0 with seed 42, and its 10% of flips between identical repeats comes from the
  server (eight thinking calls batched together, EAGLE-3), which is why its verdict is unresolved;
  `thinking_budget_live_results.md` names the serial replay as the cheapest follow-up. Then a budget
  is adopted.
- **3c.** One rented session, about $15 to $25 of the $50: the 27B against the 8B on the leader
  family and on three to five scenario seeds. The leader model is chosen on it; the rest of the
  budget is held back.
- **3d.** vLLM stays on 0.31.0. The two-minute probe becomes a standing script that includes the
  leader family. With the crowd decided by rule, `representative_response` no longer reaches the
  model in the scenario profile, so a newer vLLM may be usable there: to be measured, not assumed.
- **3e.** A fallback alert visible during a run (`progress.json`), not only in its digest.

### Stage 4. The institutional map

- **4a.** The catalogue with **ten seeds per point** (about 80 minutes of CPU), to separate a
  setting's effect from seed noise. Which cuts are expected to hold is written down before the run:
  the method and the seat rule for alternation, plurality and two-round for realignment, largest
  remainder for stasis.
- **4b.** If G2 passed: model leaders on the two or three most original cells, five to ten seeds
  each. This replaces the GPU stage `plan-scenarios-v1.md` step 6 left open, and differs from it:
  step 6 asked for 3 to 5 runs with the **model crowd** per cell; here the crowd stays rule-based
  and the model plays the leaders, in line with the scenario profile. Step 6's stage as written is
  not planned.
- **4c.** ADR-031 (a president who can lose) and ADR-032 options B, C and E are decided on the
  numbers of 2b and 4a, not before. For ADR-031 the owner also decides the test: its pre-registered
  one is a control-against-candidate design, which this plan's rules exclude.
- **4d.** A written story (`/log-run`) only for the runs kept as an archetype's example.

### Stage 5. Close-out

- **Publication, finishing what exists:** the preprint's author line and submission, and the Zenodo
  upload, prepared as a checklist with a dated note that the data predate the agency mechanisms. The
  owner submits.
- **A reference run:** one 30-year run on the scenario profile and a fresh explorer export, on the
  owner's go. The three runs of 2026-09-26 predate every agency mechanism.
- This page updated with the results, and the decision for the period after.

## 5. Open contradictions this page settles or leaves

- **Phases of the agency roadmap.** Phase 0: met. Phases 1, 2 and 3: their exit criteria were never
  assessed; ADR-031's findings (approval nearly constant, no recall) say Phase 1's would not pass.
  Phase 4: met under D11's restated criterion, on phase11 alone. Phase 5: 5.1 and 5.2 built, the
  other acts not built and parked by `plan-scenarios-v1.md`'s "stop doing".
- **The v3 milestone.** `docs/adr/v3-readiness-checklist.md` is about 1,000 citizens and is still
  open; `docs/HISTORY.md` says the gate "was passed at population 500". Both are true of different
  sizes: 500 is the largest population run, 1,000 was never run and nothing in this plan needs it.
- **The serving layer.** ADR-001 chose Ollama; the project moved to vLLM on 2026-09-10 with no ADR.
  ADR-001's status now says so and points to `plan-vllm-switch-readiness.md`.
- **The field order and compact JSON.** EXP-025 and ADR-030 say "`stance` before `shifts`" is what
  made vLLM 0.32.0 pass; production's order has it and gives 0 valid answers of 50 on 0.33.0.
  EXP-026 is the correction; the two older statements stay as dated records.
- **Left as it is:** the build order's empty "closed by" cells (the plan is a record now), the
  design document's blockers table, `docs/claude-memory/`, the tech radar's last entry, and the
  rest of `docs/overview/polity.md` (verified at a commit of 2026-10-12; only its pointer to the
  current plan is fixed here).

## Not verified

- The test count ("about 2,400" is the collected count with parametrisation), the "146 tests", the
  count of unreferenced scripts and the survey's "about two dozen" unread keys come from a
  read-only survey of 2026-11-15 and were not re-derived. Re-checked for this page: the file
  counts, the two file sizes, the ADR and OBS counts, the last behaviour commit, the nine config
  keys named in Stage 1, the catalogue figures and the EXP-026 figures.
  Stage 1 re-checks each config key and script before touching it.
- The figures quoted from results notes (catalogue shares, OBS-054, phase11, EXP-020) are quoted
  from those notes, not re-derived from run files.
- No run was made for this page. The week numbers are an order of work, not a measured duration.
