# Plan — Beyond CI: claims, research, product, memory

> **status:** live, executing since 2026-10-08. Progress is tracked in
> [`docs/STATUS.md`](../STATUS.md), not here; this file changes only when a decision does.
>
> Built from an audit on 2026-10-08:
> - three agents reviewed the live app, the content and docs, and Polity research;
> - three code-mapping passes;
> - an adversarial review of this plan;
> - my own checks.
>
> **[verified]** means re-checked against the repo. Everything else is re-checked when
> its step starts, and never fixed on an agent's word alone.

## Context

The question was "apart from CI, what should I improve? think very large". The answer
in one line: **the project checks code against code very well, but nothing checks what
it *claims*, and none of its three parts has a finish line or an outside reader.**

- **Three projects, one repo, one person.** Vote Lab is the teaching tool, Polity the
  LLM-society research, and the third is the engineering process itself.
  - In October so far, 61% of changed lines were CI/process, 23% Polity and 5% frontend.
  - The repo has 0 stars and 0 forks. Every issue was opened by the owner or a bot.
- **Vote Lab teaches some wrong things (W1).** "Method X satisfies criterion Y" lives
  in five copies, and nothing compares them.
- **Polity has never run the experiment it was designed for (W2).** That experiment is
  the comparison of two constitutions across seeds, in
  `polity-simulation-design-v2.md:36`.
- **The playground buries its own thesis (W3).** `/decouvrir` and `/a-vous-de-jouer`
  already show the right pattern.
- **The docs the agents read are stale (W4).**
- **Continuity with an earlier plan.** `PLAN_SURFACE_EXTERIEURE.md` (2026-09-16) asked
  the same question.
  - Done since: §2.B and §2.H.
  - Absorbed here: §2.I (the tour, `WinnerExplanation`, the 29-rule default) goes to
    W3; §2.G (chart accessibility) goes to W3; §2.F (an e2e winner oracle) goes to W1.

**Ground rules while this plan runs:**
- **Vote Lab and Polity alternate.** GPU runs go in the background while Vote Lab PRs
  proceed.
- **CI and process work is frozen to maintenance.** Allowed: red-build fixes, security,
  Dependabot, and any check a plan step itself needs. Not allowed: new workflows,
  gates, agents or hook features.
- **No hosted instance**, until W6 reopens the question.
- **Outside people are in scope:** one social-choice researcher and one teacher. The
  owner does the outreach; the plan prepares the material. Outreach counts as done
  when it is "sent and scheduled", since replies aren't in the owner's control.

**Intended outcome (~12 weeks):**
- **Vote Lab:** every criteria claim carries a source or a test. The content has been
  read once by an expert and tried once in a class.
- **Polity:** one result with an honest uncertainty, whatever its sign. The data is
  archived with a DOI, and there is one write-up for outsiders.
- **Status:** a 1-page `STATUS.md` anyone can read in 5 minutes.

---

## Decisions (taken 2026-10-08)

| # | Question | Decided |
|---|---|---|
| D1 | First Polity experiment (W2.1) | **The threshold's entry effect, 3% vs 5% (the default), on party founding.** Not 3% vs 7%: at 7% the assembly mostly empties (OBS-040: median 2 parties seated) |
| D2 | Tell party founders the threshold? (`agents.py:719-732`; no agent sees it today) | **Yes, as a pre-registered model change**, with an ADR-018 amendment and the prompt-neutrality harness run before and after |
| D3 | Documentation language | **English for new docs and living docs.** A living doc moves to English when it is next rewritten (W4); a one-line fix keeps the doc's language. Finished French plans are archived as they are. THEORY.md and GUIDE_UTILISATEUR, which are user-facing reference, are **not** translated in this plan. The app's FR/EN interface is unchanged |
| D4 | Where this plan lives | `docs/plan/PLAN_BEYOND_CI.md`, pointed to by `docs/STATUS.md` |
| D5 | LLM-collapse write-up (W2.6) | **A `docs/stories/` piece, then an arXiv preprint** (cs.MA / cs.CL) |
| D6 | Teacher path (W3.5) | **A `?niveau=intro` mode** over the existing pages, plus a 1-page teacher guide |
| D7 | The journal (`docs/journal/`), last entry 2026-09-27 | **Retire it** with a closing note. `STATUS.md` plus PR bodies carry the state |
| D8 | IRV, Coombs, Benham and Raynaud can fail the Condorcet-loser criterion in our engines, because tied last places are eliminated together | **Show the textbook verdict plus a variant note**, in the registry and the UI. The engines are unchanged |
| D9 | Where the claims registry lives (W1.2) | `voter-app/src/data/method_criteria.json`. The backend test reads it from the repo root |
| D10 | Teacher trial without a hosted instance | **A projector demo** run locally. Hands-on use waits for W6 |

---

## W0 — Status page and plan (Phase 0)

- `docs/STATUS.md`, at most one page: the state of each part, the next 3 steps, the
  open questions, and the CI freeze rule. Link it from `README.md` and from the
  surface table in `docs/README.md`.
- This plan, as `docs/plan/PLAN_BEYOND_CI.md`.

## W1 — Vote Lab claims: correct, single-sourced, reviewable

**Where claims live today:**

| Copy | Holds | Checked by |
|---|---|---|
| `voter-app/src/data/methodCriteria.ts:32-329` | 29 rules × 8 criteria (yes / no / conditional), shown in the Lab's `MethodsMatrix` | 1 invariant (Moulin) |
| `fast_api_voter/api/tests/test_voting_criteria_matrix.py` | 21 ordinal rules × 7 criteria, as satisfies/violates sets | Hypothesis plus pinned counterexamples: **the real evidence** |
| `voter-app/src/lib/playgroundVoting.axioms.test.ts` | a hand copy of those sets | fast-check |
| `THEORY.md`, story copy | prose | nothing |
| `voter-app/src/lib/playgroundCriteria.ts:140-149` | the map's lens: empirical, plus hardcoded random-ballot claims under other criterion names | itself |

- **Mismatches.** The table and the test sets disagree on **7 cells**: Condorcet loser
  for irv, coombs, benham, raynaud, two_round and borda, and Condorcet winner for
  bucklin.
- **Untested columns.** iia, strategy_proof, participation, reversal, and every
  cardinal row. The confirmed errors sit there.
- **The name `condorcet`.** It means Copeland in the client, the parity script and the
  UI. It means the strict criterion in the backend matrix (`:154`), in
  `gibbard_satterthwaite.py:60` and in `theory/workers.py:43`.

**W1.1 Content-fix PR (S; Phase 1)**
- **Paradox story.** **[verified]** The electorate is a cycle: Alice > Bob 402–198,
  Bob > Carol 401–199, Carol > Alice 386–214.
  - Alice "wins" the step labelled `condorcet` only because all three tie on Copeland
    score and `winCondorcet` keeps index 0 (`playgroundVoting.ts:253-277`).
  - Rewrite that step to say there is no Condorcet winner.
  - Assert in `stories.test.ts` that `condorcetWinnerIdx` (`playgroundVoting.ts:554`)
    returns −1.
  - For the squeeze and spoiler stories, also assert the strict Condorcet winner.
- **Matrix cells.**
  - **[verified]** STAR `majority` → `no`. Counterexample: 51×[5,4,3] and 49×[0,5,4]
    elects Y.
  - Re-check these against the engine before changing them:
    - participation for STAR, majority judgment and Bucklin;
    - Condorcet loser for two_round, STAR and Borda;
    - Condorcet winner for Bucklin;
    - the comment calling random ballot "deterministic" (`methodCriteria.ts:168`).
- **THEORY.md.**
  - **[verified]** :619: for 3 voters the cycle probability is 1/18 ≈ 5.6%.
  - **[verified]** :539: the chaos theorem is McKelvey's (1976/79).
  - **[verified]** :201: London's mayor used the supplementary vote, and has used
    FPTP since 2024.
  - To check against sources first:
    - :513-518 (the Arrow sketch and its scope);
    - :527 (Gibbard–Satterthwaite needs ≥3 possible winners);
    - :596 (Balinski–Young);
    - :496 (random ballot is unique only with ex-post efficiency);
    - :475 (Split Cycle against our tests);
    - :454 (the "29 methods" list).
- **i18n.** `playground.fr.ts:1296` and `playground.en.ts:1275`: manipulating Ranked Pairs is NP-complete (Xia et
  al. 2009), not "P".

**W1.2 One claims registry (M; Phase 2; held for the owner's `/reviewed`)**
1. **Settle the name.** In the backend matrix's `METHODS` (`:154`), `condorcet`
   becomes Copeland, matching `gen_engine_parity.py:86-95`. The strict criterion stays
   in `test_literature_counterexamples.py`.
2. **The registry file** (D9): `voter-app/src/data/method_criteria.json`.
   - **Shape.** One entry per (rule, criterion): `verdict`; `basis` (`engine-tested` |
     `literature` | `variant`); `source` (a bib key, required unless engine-tested);
     `note`.
   - **Frontend.** A small loader in `methodCriteria.ts` checks every rule × criterion
     and narrows the strings. A plain JSON import types them as `string`. The loader
     has its own test.
   - **Backend.** The test reads the file from the repo root, as
     `test_behavior_catalogue.py:19` does.
   - **Why under `voter-app/`.** The shipping `Dockerfile`, `audit.yml`'s image build
     and `ci-local`'s frontend and e2e images copy only `voter-app/`.
   - **CI changes this needs.** Add the path to Backend CI's paths filter, to the COPY
     lines in `ci-local/backend.Dockerfile`, and to `.mergify.yml`'s high-risk list.
3. **Consistency tests.**
   - Move the client axiom sets into a plain exported module. Importing a `.test.ts`
     from another test runs its tests twice.
   - Add a criterion name map.
   - `conditional` must carry `basis: literature` with a source, and is never compared
     with an engine set.
   - Check that:
     - the backend sets equal the `engine-tested` cells in both directions, on the 4
       shared criteria;
     - the client sets equal them too;
     - every bib key exists in `bibliography.bib`;
     - `RANDOM_BALLOT_PROPS` agrees with the registry.

Honest limit: THEORY.md and story copy stay prose. They are covered by W1.1, W1.3 and
the expert review in W1.4.

**W1.3 Story claims asserted (S; Phase 2).**
- A `STORY_CLAIMS` table next to `STORIES` (`{story, step, kind, expected, tolerance}`),
  checked by one parametrised test.
- It covers:
  - the five-candidate story, step by step;
  - the percentages in the clones, blank, monotonie, renversement and soutien stories;
  - the parliament stories' figures, which today live only in comments.

**W1.4 Reviewable and reportable (S, plus outreach; Phase 3; needs W1.3).**
- **Report path.** A "report a content error" issue form, linked from fiches, stories
  and matrix cells.
- **Cell sources.** A tooltip on each matrix cell, from the registry: its source and
  its basis.
- **Expert review.** A review packet for one social-choice researcher: THEORY.md §2–4,
  the registry as a table, and what is engine-tested.
- **E2E winner oracle.** One spec opens a story and asserts the displayed winner per
  rule via `data-testid`, against `STORY_CLAIMS`.

## W2 — Polity: one experiment, archived data, one write-up

**Why the obvious designs fail.**
- **Flagship profile.** Parties and positions never change, so the effective number of
  parties (ENP) is fixed by the seed and the threshold.
- **Blind agents.** No agent sees the threshold. Only nominees see the presidential
  method (`agents.py:424`).
- **No Duverger channel.** Ballots are sincere, there is no withdrawal, and
  `two_round` reuses one ballot, so the plurality effect predicted by Duverger's law
  has no voter-side route.
- **7% is a cliff** (OBS-040).
- **Unequal arms.** The agents-off arm has 5 fixed parties against the LLM arm's 20–30,
  so a difference-in-differences across the two is unsound.

**W2.1 Design (D1/D2): the threshold's effect on party entry** (Cox 1997; Benoit 2002).
1. **Gate probe** (minutes of GPU), in the style of `check_logprob_*_tracking.py`.
   - Give the same founder briefing with only the stated threshold changed (3, 5 or
     7%) and measure P(`found`).
   - If founding does not respond, **stop**. That is the finding, and it is cheap.
2. **Pilot.** One run on the current tip with D2 applied, timed. The GPU cap is set
   from it.
3. **Main run.** The LLM arm only: threshold 3% vs 5%, at least 10 paired seeds,
   exploration profile, amendments frozen.
   - Freezing amendments requires `regime.enabled=false` too (`config.py:1363-1366`).
   - Primary outcome: the `found` and `leave` rate per forum turn.
   - Secondary outcomes: ENP by votes, and parties on the ballot.
   - The mechanical effect comes from re-seating each run's recorded votes at the other
     threshold, on CPU.
   - Rule-driven dissolutions are reported separately (`simple_rules.py:372`).
4. **Statistics.** The primary test is an exact sign-flip permutation test on the
   per-seed differences. BCa is reported but not trusted at n=10
   (`sweep_statistics.py:49-54`).
5. **Arm M (agents off)** is kept only as a check that nothing moves without agents.

**W2.2 Instrumentation PRs (small, one each).**
1. **ENP in the outputs.** Seats-based and votes-based ENP go into `digest.json` and
   the sweep summary.
2. **Paired statistics.** A paired sign-flip permutation test plus a paired BCa in
   `sweep_statistics.py`, and an arm label on `SweepRun`.
3. **Run overrides.** `--threshold` and `--freeze-amendments` (with regime off) in
   `run_polity_flagship.py`, applied **after** `_exploration_config`. The sweep driver
   passes `--engine`, `--profile`, `--seats` and `--arm` through.
4. **Re-seating script.** It re-seats a run's recorded votes at another threshold.
5. **D2.** Founders are told the threshold, and ADR-018 is amended. The
   prompt-neutrality harness runs before and after.

**W2.3 Fit-for-inference table**, one verdict per decision type:
- validated: `vote_cast`;
- unverified: candidacy, nomination, forum `party_move`;
- collapsed: `pressure_action`, `representative_response`, `coalition_decision`.

The experiment's claim rests only on its own channel, forum founding and leaving, and
the gate probe is that channel's check.

**W2.4 Pre-registration, outside review, run.**
- Use the D9/Stage 4 template (`plan-polity-build-order.md:828-905`).
- Proof of order is the merge time, not a commit date.
- Send the pre-registration for one outside read before spending GPU time.
- Run it through `gpu_queue.sh`.

**W2.5 Archive.**
- What goes in: the three 30-year runs and the experiment's runs, call logs included.
- Upload to Zenodo for a DOI. Add `CITATION.cff`, and pin vLLM by digest.
- Check `llm_prompts.jsonl` for local paths before publishing.

**W2.6 Write-up.**
- A `docs/stories/` piece on the logprob instrument: an aggregate metric conforms
  while every individual decision has collapsed, and the collapse persists across
  model families and across base vs instruct.
- Then the preprint (D5).

**Later, not in this plan:** run-level cross-model replication, prompt variants, and the
presidential Duverger design.

## W3 — Playground: show the thesis on every screen

The model is `/decouvrir`, the home hero and `/a-vous-de-jouer`: the same ballots give
a different winner, with one sentence saying why.

**W3.1 Quick fixes (S; Phase 1)**
- **One candidate palette.** **[verified]** Carol is green on the map and red in the
  Bilan.
  - Replace `CANDIDATE_COLORS_LIGHT` with `candidateColor(i)` at its 7 importers, and
    in the local palettes.
  - Check contrast in light and dark mode.
- **Scroll reset.** A `ScrollToTop` inside the Router, triggered on pathname change
  only. Navbar links are plain `<a>`, so test it from a `<Link>` path.
- **Remove the onboarding tour.** Move the e2e locators that use `data-tour` to
  `data-testid`.
- **English mode.**
  - `MethodsMatrix` and `NonSpatialProfileMap` use `useVotingLabels()`.
  - Set `<html lang>` inside `switchLanguage` and at init.
  - Translate the leftover French strings.
- **One method count.** "29 selectable methods" via `{{count}}`, in the UI, the meta
  tags and the PWA manifest.
- **`/polity` out of the main nav.** The route stays.
- **Charting library on every page.** React lands in the recharts manual chunk. Fix the
  chunking, and verify the home page no longer preloads `recharts-*`.

**W3.2 Winner on every step, 5 methods by default (M; Phase 2).**
- A winner strip on every step.
- A new `INTRO_RULES` next to `LEADER_RULES` (`lib/scorecard.ts:87`) becomes the default: plurality, two-round, IRV, approval and Condorcet (Copeland), close to `DEMO_RULES` (`DecouvrirPage.tsx:37`).
- The lottery is labelled "no fixed winner".

**W3.3 "Why" in the Bilan (M; Phase 3).**
- `WinnerExplanation` per winner group, plus a sentence comparing two methods.
- The traces come from the full electorate.

**W3.4 Phone story layout (M; Phase 3).** The narration and the map stay on screen
together.

**W3.5 Class mode (M; Phase 4; D6, D10).**
- `?niveau=intro`: `INTRO_RULES`, 4 stories, and about 8 Lab fiches that don't need
  the backend.
- A 1-page teacher guide for a 45-minute projector lesson, in FR and EN.

**W3.6 Accessible results (Phase 4).**
- `aria-live` announcements of winner changes.
- A text summary of the map, and a `ParliamentCanvas` label that carries data.
- Touch targets of at least 44 px on phone.

**Measure only:** phone drag jank (about 800 ms of blocking work per second of drag,
with the CPU throttled 4×).

## W4 — Memory and docs (S, Phases 0–1)

- **Drift fixes.**
  - The memory snapshot's `--base develop` rule and its v8 merge rule.
  - README's workflow, and the count of tool trials.
  - "26 methods locked" → 28.
  - `traceability.md`'s claim that polity has "no code link".
  - The status of `PLAN_SURFACE_EXTERIEURE` §2.B.
  - Two plans that say "gitignored" but are committed.
- **Archive the finished plans** under `docs/plan/archive/`. Live plans carry a
  `status:` line, and `docs/README.md` gets a plan index.
- **Journal (D7).**
  - Add a closing note.
  - Remove the journal surface from `docs/README.md`.
  - Deleting `/log-session` and `journal-writer` is a `.claude/` change and is held for
    `/reviewed`.
- **Living docs to English (D3), when touched.**
  - The PR template, `CLAUDE.md`, `/verify` and `spec-checker` change in **one PR**,
    because the template's section names are quoted in all four.
  - The French-language agent and command prompts change when next edited.

## W5 — Engine correctness backlog (M; Phase 3; held for `/reviewed`)

- **What:** the listing-order tie issues #662–#667, per `LISTING_ORDER_TIES.md`.
- **Order:** #666 first, so the others have a test that can fail.
- **Test:** reversed candidates must give the same result.
- **#667 is parity-locked:** fix both engines and regenerate the fixture.
- **Not here:** the simultaneous-elimination variant (D8).

## W6 — Hosting, revisited (Phase 4)

- **Spike, at most 2 days:** the non-Polity engine in Pyodide inside a Web Worker, for
  2–3 Lab fiches.
  - **[verified]** Those modules import only numpy, scipy, pydantic and the stdlib.
- **Compare with:** the existing container on Fly, after `PLAN_SURFACE_EXTERIEURE`
  §2.A and §2.D.
- **Output:** a one-page memo, and the owner decides.

---

## Sequencing (~12 weeks)

| Phase | Vote Lab | Polity | Docs / other |
|---|---|---|---|
| 0 · wk 1 | — | W2.2 item 5 (D2 founder briefing + ADR-018) | W0, W4 drift fixes + journal close |
| 1 · wk 1–3 | W1.1 content fixes; W3.1 quick fixes | W2.2 instrumentation; W2.3 fit table; W2.1 gate probe | W4 living docs to English |
| 2 · wk 3–6 | W1.2 registry; W1.3 story claims; W3.2 winner strip | pilot → W2.4 pre-registration + outside review → runs; W2.5 archive | W2.6 story draft |
| 3 · wk 6–9 | W1.4 review packet → researcher; W3.3 "why"; W3.4 phone | analysis + write-up | W5 tie bugs |
| 4 · wk 9–12 | W3.5 class mode → teacher; W3.6 | preprint | W6 spike + decision; close the plan |

Each phase ends with a `STATUS.md` update. The CI freeze lifts at the end of Phase 4.

**If it slips, cut in this order:**
1. W6, unless the teacher trial needs it.
2. W5 #663 and #664.
3. W3.4 and most of W3.6.
4. The preprint. Keep the `docs/stories/` piece.

If the W2.1 gate probe stops the experiment, Polity's Phase 2–3 slots go to W2.6.

## Verification

**Every PR:**
- a branch from `polity`;
- `/code-review` before opening;
- `/verify "<request verbatim>"`;
- the PR template's sections, including **Non vérifié**.

High-risk paths wait for the owner's `/reviewed <sha>`.

**By workstream:**
- **W1.** Every new guard test fails on the current tip first. `docker build` still
  succeeds after W1.2.
- **W3.**
  - e2e tests anchor on `data-testid`.
  - Before/after screenshots at 1440×900 and 390×844, in FR and EN.
  - The built home page does not preload `recharts-*`.
- **W2.**
  - The statistics are unit-tested on synthetic data with a known effect.
  - The ENP fields appear in a deterministic run's digest.
  - The re-seating script reproduces a recorded run's seats.
  - The pre-registration is merged before the first GPU run.
  - One archived run replays to its digest.
- **W4.** `doc-drift` runs clean. The 5-minute test: from `STATUS.md` alone, name the
  next 3 steps.
- **W5.** Reversed-order tests pass, parity is regenerated, and `oracle_diff_report` is
  in the PR.
