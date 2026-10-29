# Roadmap to Milestone 1: fix, test, clean, then one result from the LLM society

> **status:** live — set 2026-10-29 from a review of the project; nothing in it is built yet.
> (`docs/README.md` lists every plan.)

**What this is.** The order of work from today's `polity` tip (`57b8a10`) to a first milestone
the project can build on. It has four phases, in strict order: **F**ix what is broken, **T**est
the fixes and set the baselines, **C**lean without changing a run, then **M1**, one
pre-registered experiment with a verdict. Each phase has an exit gate. The next phase does not
start until that gate is met.

**Why this order.** The review of 2026-10-29 found Polity is not blocked by a technical wall.
Three things hold it back:

- The question keeps moving: design v2, ADR-011, the agency roadmap, the threshold experiment,
  scenarios v1 and the catalogue, with no finished claim between them.
- The part that needs the LLM has not run since the 8B baseline of 2026-10-21. The catalogue
  that meets step 6's gate runs on the rule-only twin, where the president, the amendments, the
  forum and party founding are off (`_exploration_config` ties them to `config.llm.enabled`).
- New mechanisms ship off (ADR-032 D, ADR-036, ADR-040), which adds surface without adding a
  result.

The cure is a short list of fixes, a baseline to compare against, and one question only the LLM
can answer.

**Ground rule until M1 exits.** No new mechanism, no new ADR, no new profile, unless an item
below names it. A finding that would need one goes into `observations.md` as an OBS and waits.

**Target dates** (planning targets, not commitments): F by 2026-11-05, T by 2026-11-12, C by
2026-11-19, M1 by 2026-12-03.

---

## Phase F — Fix what is broken

| # | What | Where | Done when |
|---|---|---|---|
| F1 | **Mutation Testing has been red on `polity` since 2026-10-12** (issue #920, the only line left on it; last green 2026-10-10, run 38050715101). The 2026-10-26 run fails in Stryker's dry run ("There were failed tests in the initial test run"). The journal traced it to `methodCriteria.test.ts:120`, which reads `../../../docs/research/bibliography.bib`, a file outside Stryker's sandbox (#899). Fix: give the test the file inside the sandbox (Stryker's file list, or a small generated module the test imports). Re-check the cause on the current log first. | `voter-app/src/data/methodCriteria.test.ts`, `voter-app/stryker*.json` | #920 closes on its own (`branch-red-alert.yml`) |
| F2 | **Show the schema the prompts point at (OBS-053).** 18 prompts say "in the schema given" or "conforme au schema fourni" but never show it (4 in `agents.py`, e.g. `:303`, `:673`, `:816`, `:882`; 14 in `llm_behavior_engine.py`). The 27B spends its reasoning rebuilding the schema and never shifts a forum view (0 of 495). Fix: render the fields, in their declared order (ADR-030), into the prompt text. This changes every agent prompt's fingerprint, so it is a measured change: a bake-off on the local 8B before and after, reporting reasoning tokens, the share of reasoning spent on the format, and the forum's shift rate. | `agents.py`, `llm_behavior_engine.py`, `scripts/run_bakeoff.py` | Merged with its bake-off table, and OBS-053 re-statused |
| F3 | **Decide the thinking budget for agent turns (OBS-054)**, from F2's bake-off: the budget binds on 62–100% of leader and chamber calls on both models (`plan-rented-gpu-runs.md` §11). The owner decides. | `llm.thinking_token_budget` | One value recorded in the scenario profile, with its reason |
| F4 | **One society, two engines.** The scenario profile is not the same society on the twin and on the model: the turnout cost is 0.02 on the twin and 0.04 with the model (`LLM_TURNOUT_COST`, `run_polity_flagship.py:110`, `:229`, `:322`). Fix: one turnout cost for both. 0.02 is the only value with a calibration behind it (ADR-039), and the owner decides. Then add a test that lists every field where the scenario profile differs between the two engines and fails on any field that is not part of the agent tier (`agents.*`, `parties.birth_enabled`/`death_enabled`, `regime.enabled`, `llm.*`). | `scripts/run_polity_flagship.py`, `api/tests/test_polity_flagship_experiment_overrides.py` | The test is merged, and the only difference it allows is the agents |
| F5 | **Two CI gates that lie.** #682: the 90% backend coverage floor passes from 89.5%. #681: the nightly flaky check hides 28 benchmark tests that fail on every run. Both were opened on 2026-09-28 and are untouched. Any part that is a workflow edit is the owner's (the push token has no `workflow` scope). | `codecov.yml`, `scripts/check_flaky_backend.py`, the workflows | Both closed, or each has the owner's patch in its body |
| F6 | **The project's own status page is two weeks behind.** `docs/STATUS.md` was last touched on 2026-10-13. It never mentions scenarios v1, the catalogue or ADR-033 to ADR-040, and its "next 3 steps" are done (Playwright 1.64 is in, the static-site workflow edits are in). Rewrite it against this roadmap. In `docs/README.md`, `plan-polity-agency-roadmap.md` and `plan-polity-build-order.md` are still listed as live, though `plan-scenarios-v1.md` has replaced them in practice. Re-status them. | `docs/STATUS.md`, `docs/README.md`, the two plans' headers | `doc-drift` reports nothing on those files |

**Exit F:** F1–F6 done; `polity` green on every workflow, Mutation Testing included.

## Phase T — Test: prove the fixes, set the baselines

T1–T3 and T6 need no GPU. T4 and T5 need about one GPU day, local or rented.

| # | What | Done when |
|---|---|---|
| T1 | **The gates on the tip:** `scripts/fast-gate.sh`, then `ci-local/`, on the commit that closes Phase F. Any `SKIPPED` section is written down as not verified. | A clean run, recorded in this file |
| T2 | **The instrument reproduces itself:** re-run catalogue sweep 5 (`run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`, then `report`) on F's tip. F4 changes the LLM side only, so the twin's numbers should not move. If they do, find out why before going on. | Same archetype counts and band count as `run_polity_catalogue_results.md` |
| T3 | **The seed-noise yardstick:** the same 1,000-run budget (about 8 minutes), arranged as 100 points × 10 seeds instead of 1,000 points × 1 seed. It gives, per configuration, how far two runs drift apart by seed alone (`trajectory.pairwise_distances`). It also shows which PRIM boxes survive once the seed is not mixed in: the negative control already showed up once as an edge trim in sweep 3. This is the yardstick M1 measures against. | A results file with the within-configuration distance distribution and the boxes that survive |
| T4 | **Time the model arm of the scenario profile** (open since step 2): one LLM run of the scenario profile, 8 years, population 100, the 8B, on F's tip. Report the wall time, calls per tick by decision, retries and fallbacks per decision type. This prices M1. | Timed, with every decision type under 5% fallback (or an OBS saying which one is not and why) |
| T5 | **The model arm is reproducible:** replay T4's call log and check the journal is byte-identical (the EXP-020 protocol). | Byte-identical |
| T6 | **Pick M1's cells:** from T3, three configurations whose seed noise is small enough for a difference to show, one from each of three different archetype regions. Write them down before any M1 run. | Three configurations in the pre-registration (M1.1) |

**Exit T:** T1–T6 done. The seed-noise table and T4's cost are committed.

## Phase C — Clean, time-boxed to one week, without changing a run

**The rule of this phase:** every change must be proven behaviour-preserving by three checks:
(a) T4's call log replays byte-identically, (b) the twin reproduces T2's numbers, and (c) the
golden and behaviour-catalogue tests pass. A change that cannot be proven this way is dropped
from C and waits until after M1. The replay harness is the project's best refactoring safety
net. This phase is where it pays off.

| # | What | Done when |
|---|---|---|
| C1 | **Inventory of the knobs.** `PolityConfig` has about 258 fields. Write a script that prints, for each one: its default, which profiles set it, whether the catalogue varies it, and whether any test sets it to something other than its default. Commit the table. Fields that no profile, catalogue dimension or experiment uses are listed for the owner, who marks each as experimental or deletes it. | The table is committed, and every unused field has the owner's verdict |
| C2 | **The profiles as data.** `_flagship_config`, `_exploration_config` and `_scenario_config` carry their calibration history in their docstrings (`_scenario_config`'s is about 20 lines). Move that history to the ADRs it already cites, and keep one line per setting in the code. Optionally, move the profiles to YAML, with a test that each one reproduces today's `config_hash`. Only if C1 shows it is cheap. | Docstrings cite ADRs; `config_hash` unchanged |
| C3 | **The open OBS against the scenario profile.** 13 OBS are open and OBS-054 is unresolved. Several are about crowd decisions the scenario profile no longer sends to the model (OBS-007, 011, 013, 024). Give each one a line saying whether it applies to the scenario profile, and re-status the ones that do not ("out of scope for the scenario profile") rather than closing them. | Every open OBS has that line |
| C4 | **The old CI issues** (#683, #690, #691, #692, #694, #833): fix, or close with a reason, or mark "after M1" explicitly. Workflow edits are the owner's. | None left without a decision |
| C5 | **Optional: split the two largest files** along their existing seams. `llm_behavior_engine.py` (5,499 lines) splits into its nine decision specs; `run_polity_simulation.py` (3,581) into its tick phases. Only if the replay stays byte-identical and the provenance's prompt-file hashes do not change. Moving prompt text between files would change those hashes. Otherwise, after M1. | Replay byte-identical, or skipped with a note |

**Exit C:** C1–C4 done; C5 done or deferred. T2's numbers and T4's replay are unchanged on C's tip.

## Milestone 1 — Do LLM leaders change the trajectory?

**The question.** In the scenario profile, holding the society fixed, do runs whose leaders are
played by the model produce trajectories that are distinguishable, beyond seed noise, from the
same runs with leaders played by rule? If so, which of Laver and Sergenti's four types (Sticker,
Aggregator, Hunter, Explorer; ADR-040) does the model's behaviour look like?

This is the question the LLM has to answer to justify its cost. Both answers are results:
- **Yes:** the agent tier matters. It unlocks step 7's classification, ADR-031 option B and the
  catalogue's GPU stage.
- **No:** the twin is the instrument, and the model is kept for what only text can do (the
  forum, the limit-testing log). That saves the GPU and points the next work at the society
  itself (below).

| # | What | Done when |
|---|---|---|
| M1.1 | **Pre-register** with `scripts/llm_test_harness/` before the first run. It records: T6's three configurations; the arms; the seeds (10 per configuration, the same seeds in every arm); the primary outcome; the decision rule; and a GPU budget cap set by the owner. | Registered and committed before any M1 run |
| M1.2 | **The arms.** One model arm: the 8B with F2 and F3 in, the agent tier on. Four rule arms: the twin with `parties.leader_rule` set to each of the four types. F4's test is the written list of what differs between them. Cost: 30 model runs (3 × 10, about 30 GPU hours at today's 8-year p100 figure, to be replaced by T4's measurement) and 120 twin runs (minutes). | All runs finished, their call logs archived |
| M1.3 | **The primary outcome.** Per configuration: the trajectory distance (`trajectory.pairwise_distances`) between the model arm and the nearest rule arm, compared with T3's within-configuration seed noise by a permutation test. H0: the model arm is within seed noise of at least one rule arm. | One verdict per configuration, computed by a committed script |
| M1.4 | **Secondary outcomes.** Which rule type the model's yearly platform moves are closest to; the divergence test (i)–(iv) per arm; the fallback and retry rates. | In the results file, labelled as secondary |
| M1.5 | **Write it up:** a results file next to the script, an OBS for anything strange, the verdict in `STATUS.md`, and the archive of the runs in the same Zenodo deposit as W2.5 (the owner's upload). | Results reproducible from the archived call logs by one command |

**Exit M1:** M1.1–M1.5 done, with the verdict stated whichever way it goes. That is the
milestone to build from.

## In parallel, not blocking M1

- **Submit the preprint** (`docs/preprint/`, D5): the author line and the disclosure are the
  owner's. It is the project's finished result today. Submitting it gives the work a date.
- **Vote Lab, #926:** the ranked rules, IRV and Coombs on a full tie, the tallies that still
  break ties by name, and approval. It regenerates the parity fixture, so it goes through
  `gen_engine_parity.py` and the parity test, never by hand.
- **Outreach** (W1.4, W3.5): the researcher's packet is ready; the teacher demo waits on a
  contact.

## After M1: what to build from

In this order, each one judged by the divergence test against M1's arms:

1. **Heterogeneity in the society**, the most likely cause of the band failures. Every turnout and
   panel-stability failure in sweeps 4 and 5 is on the high side. Three settings are the same for
   every citizen: the turnout cost (ADR-039), economic voting, which swings whole blocs
   (ADR-038), and shock salience on the rule path (ADR-033). Making each of them vary by citizen
   comes before any more calibration.
2. **Whichever branch M1's verdict opens:** step 7's model classification and ADR-031 option B
   (yes), or the twin catalogue with 10 seeds per point (no).
3. **Only then, new mechanisms.**

## Decisions waiting on the owner

| When | Decision |
|---|---|
| F3 | The thinking budget for agent turns |
| F4 | One turnout cost for both engines (0.02 proposed) |
| F5, C4 | The workflow edits (the push token cannot push them) |
| C1 | The fate of each unused knob |
| M1.1 | The GPU budget cap, and local vs rented |
| M1.5 | The Zenodo upload |
| Anytime | The preprint's author line |

## Not verified

- The Mutation Testing cause comes from the journal of 2026-10-12. The 2026-10-26 log only says
  the dry run has failing tests. F1 re-checks the cause first.
- The 30 GPU hours of M1.2 extrapolate the 8B exploration run of 2026-10-21 (61 minutes, 8
  years, p100, 24 workers). The scenario profile caps the forum at 10, so it may be cheaper.
  T4 measures it.
- No test or simulation was run for this plan.
