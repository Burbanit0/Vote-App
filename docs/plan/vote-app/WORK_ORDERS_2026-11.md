# Work orders: what is left of the global plan, one session at a time

> **status:** live. Written 2026-11-14 on `polity` at `ff2dbaf1`. It turns what is left of
> [`PLAN_GLOBAL_2026-11.md`](PLAN_GLOBAL_2026-11.md) into work orders that a Claude Code
> session can pick up with no memory of the sessions before it. The global plan says *what*
> and *why*; this page says *who does what next, starting where, and when to stop*.
> `CLAUDE.md` still rules: where this page and `CLAUDE.md` disagree, `CLAUDE.md` is right and
> this page is to be fixed.

## How a session uses this page

1. **Read** `CLAUDE.md`, then this page down to "Work orders". Read the global plan's
   paragraph for the phase you are about to work in.
2. **Pick** the first work order, in the order of the table below, that is not done, not
   claimed and not blocked. Do one work order per session unless the owner says otherwise.
3. **Check it is not claimed.** A work order is claimed when its branch exists on the remote
   or a PR carries it, open or merged (a merged PR's branch is deleted, so ask both):
   ```bash
   git fetch origin
   git ls-remote --heads origin '<branch of the work order>'
   gh pr list --state all --head '<branch of the work order>'
   ```
   For a work order done in several PRs (P5-1's batches), ask for the prefix:
   `git ls-remote --heads origin 'refactor/use-simulation-*'`.
   If either answers, someone has it, or it is done and the status table is late: fix the
   table in your own PR and take the next one. Push your branch early (an empty first commit
   is fine) so the next session sees your claim.
4. **Do it** under "Rules that do not bend" and "The gate list", in a worktree (see "Local
   traps").
5. **Tick it** in the status table of this page, in the same PR: write `open` and the branch
   name. The owner's merge is what makes it done; the next session changes `open` to `done`
   when it finds the PR merged.
6. **Stop** when the PR is open and you have read its CI (the real log of any failure, not
   the job's name). Report: what was done, what was checked, what was not, what the owner
   must decide. Do not start the next work order while a question to the owner is open on
   this one.

A work order marked **blocked** needs an answer from the owner first (see "Decisions that are
the owner's"). Ask the question; do not answer it yourself.

## Rules that do not bend

- **Never** merge a PR, post the review command, add a `reviewed` label, or set a
  `human-review` or `High-risk review gate` status. Approval and merge are the owner's alone.
- One branch per work order, cut from `origin/polity`, PR against `polity`. Names:
  `feat/*`, `fix/*`, `refactor/*`, `ci/*`, `chore/*`, `docs/*`, `test/*`.
- Run `/code-review high` once on the branch **before** opening the PR. Each finding is a
  claim: check it against the code, fix the real ones, say in the PR which you left and why.
- Run `/verify "<the work order's Request, verbatim>"` before opening the PR. `FAIL` means
  no PR. `GAPS` means the gaps are written in the PR.
- The PR body has `## Request` (verbatim), `## Acceptance criteria`, `## Evidence` (commands
  actually run, with their output) and a **Not verified** line that is never empty unless
  it is true.
- Never hand-edit `engineParity.json` or any other generated oracle. Regenerate it, and say
  in the PR what the regeneration changed.
- **Release 0.4.0 comes after every work order here is done** (the owner's instruction,
  2026-11-12). No version bump before that.
- Polity is out of scope, and the main checkout may hold someone's uncommitted Polity work
  on another branch. Do not touch it, do not stash (the stash is shared by every worktree).

## Local traps (each one cost a session time)

- **Work in a worktree**, not in the main checkout:
  `git worktree add --no-track -b <branch> <scratch dir>/<name> origin/polity`, and push with
  `git push -u origin HEAD`. Without `--no-track` the branch's upstream is `polity` itself,
  and git's own hint for the failed push is a direct push to `polity`: never follow it.
  Remove the worktree when the PR is merged.
- **`/code-review` and `/verify` run in the session's own directory.** From a worktree, give
  them the branch and the worktree path in so many words, then check that the findings talk
  about your files. A review once came back with nine findings about another branch's
  uncommitted files.
- **`node_modules`:** run `npm ci` in the worktree's `voter-app/`. A symlink to the main
  checkout's `node_modules` works only while that one matches the lockfile: on 2026-11-14 it
  had jsdom 30 where `package.json` asks `^31`, and four tests in `HomeEntrance` and
  `StoriesRegister` failed for that reason alone. Before calling a local failure a
  regression, run the same test on a clean `origin/polity`.
- **Python:** `fast_api_voter/mypy.ini` targets Python 3.14, and on 2026-11-14 both the
  system `python3` and the main checkout's `fast_api_voter/.venv` were 3.13. With no 3.14 on
  `PATH`, `scripts/fast-gate.sh` and `/verify` print `SKIPPED` for the backend sections
  (mypy, pytest, the parity and OpenAPI drift checks). A `SKIPPED` section is not a pass: CI
  is then the only check, and the PR says so under Not verified. That venv runs pytest on a
  file well enough to develop with (call its `python` by full path), but its packages can
  lag the lockfile, like `node_modules` above.
- **The shell is zsh on macOS:** quote every glob (`--include='*.py'`), there is no
  `timeout`, and `sed -i` needs `sed -i ''`.
- **A command whose text contains the review command is refused by a hook**, even inside a
  PR body. Describe the hold ("held for the owner's review of this head") without writing
  the command.
- **Port 3000 may already serve another tree.** The Playwright config reuses a server it
  finds there, so `npm run test:e2e` can pass against code that is not yours. Check what
  listens, or run your spec with a copy of the config on another port (build with
  `vite build --outDir node_modules/.e2e-build-<name>`, serve with `vite preview --port
  <other>`), and delete the copy afterwards.
- **Local WebKit dies at `page.goto`** ("WebKit encountered an internal error") when the shell
  was started from the VS Code snap (Linux): the snap leaks `GIO_MODULE_DIR`, a module cache
  built against the snap's older glibc, and WebKit's network process loads it
  (`DEBUG=pw:browser` shows `symbol lookup error: /snap/core20/.../libpthread.so.0`). Nothing
  else of the snap's environment matters. Run `env -u GIO_MODULE_DIR npx playwright test
  --project=webkit …`. To see a WebKit-only race, add load: `yes > /dev/null` a couple of times
  per core and `--workers` equal to the cores (stop them with `pkill -x yes`, never `pkill -f`,
  which matches your own shell).
- **Visual baselines** are rendered in the pinned Playwright image
  (`voter-app/scripts/test-visual-docker.sh --update-snapshots`, needs Docker and the backend
  on `:4434`). Without Docker: let the PR's "Visual regression" job fail once, download its
  `playwright-report-visual` artifact, look at the diff image, and commit the job's *actual*
  image as the new baseline. Say so in the PR. A regenerated baseline holds the PR for the
  owner.
- **The quality ratchet fails when a count rises and when it falls**
  (`.github/quality-baseline.json`). Measure before opening the PR, from `voter-app/`:
  `npx eslint -c eslint.sonarjs.config.js . --ext .js,.jsx,.ts,.tsx | tail -3`,
  `npx knip --no-progress`, and from the root
  `npx --yes jscpd@5.4.0 --config .jscpd.json fast_api_voter/api voter-app/src | tail -3`.
  Those are the three frontend counts. The four backend ones (vulture, radon, deptry, strict
  mypy over `fast_api_voter/scripts/`) are measured by the `code-quality` job of
  `audit.yml`: copy its commands, a new script under `fast_api_voter/scripts/` can raise
  `mypy_scripts`. If your change removes debt, the baseline must come down in the same PR,
  and the PR is then held (`.github/quality-baseline.json` is on the hold list).
  `scripts/check_quality_ratchet.sh --update` rewrites it, but it reads the seven report
  files the job writes with `tee` (`voter-app/knip.txt`, `voter-app/sonarjs.txt`,
  `jscpd.txt`, and four under `fast_api_voter/`) and refuses to run without all of them.
  Work order P6-4 removes this chore.
- **diff-cover wants 100% of changed lines and branches.** Locally:
  `npx vitest run --coverage --coverage.reportOnFailure=true`, then
  `diff-cover voter-app/coverage/cobertura-coverage.xml --compare-branch=origin/polity
  --branch-coverage --fail-under=100` (install `diff-cover` into a scratch directory with
  `pip install --target`, never into the repo).
- **dependency-cruiser's `no-circular` counts type imports.** A type that a `lib/` module
  and a component both need lives in `lib/` (`electionTypes.ts`; `journeyTypes.ts` arrives
  with PR #1080, do not create another).
- **A new backend test file that imports `simulation_ranked_utils` or
  `simulation_score_utils`**, and uses neither `TestClient`, FastAPI, numpy nor `api.main`,
  must be added to the mutmut selection list in `fast_api_voter/pyproject.toml`:
  `test_mutmut_selection` fails until it is. Add no other file to that list (an API test
  there breaks mutmut's in-process reload, and nothing local would tell you), and note that
  `pyproject.toml` is on the hold list.
- **A new i18n key** goes in `playground.fr.ts` (the source), `playground.en.ts`, then
  `npm run gen:pseudo-locale`.
- **Mutation-check your own tests by hand:** alter each changed line in turn and rerun the
  tests. A line whose alteration no test notices is either untested or dead. Say in the PR
  which mutants survived and why they are equivalent.

## The gate list

`scripts/fast-gate.sh origin/polity` is the quick subset. Before a PR, run the whole list of
the side you touched.

Frontend, in `voter-app/`: `npm run lint`, `npx tsc --noEmit`, `npm run type-coverage`,
`npm run depcruise`, `npx vitest run --coverage` with diff-cover, `npm run build`, the three
ratchet counts above, and the Playwright specs of the pages you touched, on a production
build.

Backend, in `fast_api_voter/`: `mypy api/`, `python -m pytest <paths> -o addopts="" -q` for
speed, then the coverage run that CI enforces (`ci-local/` mirrors it), and `ruff`.

Either side of the voting engine: `PYTHONHASHSEED=0 python
fast_api_voter/scripts/gen_engine_parity.py`, then `npx vitest run
src/lib/playgroundVoting.parity.test.ts`. A parity break is a bug until proven otherwise.

## Decisions that are the owner's

A session asks these; it does not settle them. Each is tied to the work order it blocks.

| # | Question | Blocks |
|---|---|---|
| D1 | PR #1080 holds a regenerated visual baseline: review of head `ac51c001`. And: should the visitor's previous scenario survive a reload after a link replaced it (today it is kept in memory only, and the notice says so)? Are the two analytics events wanted? **Answered 2026-11-15: keep it in memory only; keep both events.** | nothing: a follow-up to P2-1 (#1080 is merged), closed |
| D2 | Adding an entrant on the map (#1078) is a double-click, in the Électorat moment only, with no touch equivalent. Keep, or an armed single-click mode, other moments, touch? | nothing; a follow-up if changed |
| D3 | Hotelling moves its candidates in list order, and identity voting binds its default groups to the first and second listed candidates. Neither is a tie. Change them, or record them as by design? **Answered 2026-11-15: Hotelling's order is drawn by lot; identity voting's default groups back the candidate nearest their centre (the owner chose over drawing the pairing by lot, which would make the default arbitrary against ideology); the apportionment comparison is by design.** | P3-4, decided |
| D4 | Where the two engines, or two rules, treat a truncated ballot differently (P3-5 produces the table): which reading wins, rule by rule? | P3-6 |
| D5 | One electorate for both engines: send the client's voters to the backend, or lock the sampler, turnout, scores and scorecard axes with a second golden fixture? | P3-7 |
| D6 | Phase 4 is "not urgent while only the static site is public". Is it still part of what 0.4.0 waits for? | the order of Phase 4 |
| D7 | Which paths leave the human-review hold list? And "CI health check" is a required status: making it advisory means changing branch protection, which only the owner can do. | P6-1, P6-2 |
| D8 | Polity's own CI job and requirements file touch Polity, which has its own plans and work in progress. When, and on which branch? | P6-5 |
| D9 | Each Phase 7 feature starts with a one-page design note the owner agrees to. | P7-1, P7-2, P7-3 |

## Status

`todo`, `open` (a PR exists: name the branch), `done` (merged), `blocked` (see the decision).
**Held** means the PR waits for the owner's review of its head commit; plan for one extra
round trip. Two things hold a PR: touching a path of `.mergify.yml`'s hold list (the
engine, workflows, gate scripts and configs, `docs/spec/`, regenerated oracles, the quality
baseline), and weakening the test suite (fewer tests in a changed test file, or an added
skip, only or xfail: `scripts/check_test_integrity.py`). The column is a forecast, not a
promise: read the "Decide whether the PR is held for review" job on your own PR.

| ID | Work order | Held | Status |
|---|---|---|---|
| P2-1 | Shareable scenario link | yes (visual baseline) | done: PR #1080 (merged); D1's follow-up questions stay open |
| P2-2 | Strike Phase 2 in the plan and `STATUS.md` | no | open: `docs/phase-2-done` |
| P3-1 | Ranked pairs and River: equal locks by lot | yes (engine) | done: PR #1083 (merged); the lock order's first PR had a perf regression on tie-heavy profiles, see its description |
| P3-2 | Kemeny-Young: equal rankings by lot | yes (engine) | open: `fix/kemeny-equal-rankings`, PR #1088 |
| P3-3 | Theory tally, multiwinner fallback, runners-up by lot | yes (engine file) | todo |
| P3-4 | Hotelling, identity voting, apportionment comparison; close #926 | no, unless D3 changes an engine file | open: `fix/ties-last-entries`, PR #1092 |
| P3-5 | Truncated ballots: write down and pin what each rule does today | yes (`docs/spec/`) | todo |
| P3-6 | Truncated ballots: one convention, one pairwise-defeat definition, Hypothesis strategies | yes (engine) | blocked: D4, after P3-5 |
| P3-7 | One electorate for both engines | yes | blocked: D5 |
| P3-8 | Validate the three one-string UI keys | no | todo |
| P4-1 | Throttle the Socket.IO Monte-Carlo | yes if it edits `ratelimit.py` | todo (D6 for the order) |
| P4-2 | Key the rate limiter on the real client address | yes (`ratelimit.py`) | todo |
| P4-3 | A per-request work budget, and timeouts that stop the work | no | todo |
| P4-4 | A per-fiche error boundary | no | todo |
| P4-5 | Finish #692: pin images and pip installs by hash | yes (workflows) | todo |
| P5-1 | One `useSimulation` hook, then the panels in batches | yes once jscpd falls (baseline) | todo |
| P5-2 | Monte-Carlo and grid libraries in a Web Worker | no | todo |
| P5-3 | Typed nested API responses | yes (OpenAPI contract) | todo |
| P5-4 | Split `AVousDeJouerPage` and `LeaderCanvas` | no | todo |
| P6-1 | Observer workflows into one daily job; "CI health check" advisory | yes (workflows) | blocked: D7 |
| P6-2 | Narrow the human-review hold list | yes (`.mergify.yml`) | blocked: D7 |
| P6-3 | Group Dependabot's updates | no (`dependabot.yml` is not on the list) | todo |
| P6-4 | The ratchet lowers its own baseline and runs locally | yes (`scripts/check_*`) | todo |
| P6-5 | Polity's own CI job and requirements file | yes (workflows) | blocked: D8 |
| P6-6 | A scheduled advisory check of the Playwright image digest | yes (workflows) | todo |
| P7-1 | Bring your own ballots (paste, CSV, PrefLib) and export | no | blocked: D9 |
| P7-2 | Predict-then-reveal and challenges | no | blocked: D9 |
| P7-3 | Class mode | no | blocked: D9 |
| R-1 | Release 0.4.0 | n/a | after everything above |

## What may run at the same time

Two sessions collide when they edit the same file or regenerate the same oracle. Lanes:

- **Engine lane, one session at a time:** P3-1, P3-2, P3-3, P3-5, P3-6, P3-7. They share
  `simulation_ranked_utils.py`, `playgroundVoting.ts` and the parity fixture; a second
  regeneration on a stale base is a conflict in a generated file. Rebase on `origin/polity`
  and regenerate again after every merge in this lane.
- **Playground lane, one at a time:** P5-1, P5-2, P5-4 (they all pass through
  `PlaygroundController.tsx`, `LeaderCanvas.tsx` or the panels).
- **Backend robustness lane, one at a time:** P4-1, P4-2, P4-3. P4-1 and P4-2 both pass
  through `api/core/ratelimit.py`, and a changed request bound regenerates the OpenAPI
  contract and `types.gen.ts`, which P5-3 regenerates too. P4-5 belongs to the CI lane.
- **CI lane, one at a time:** P4-5, P6-1 to P6-6 (workflows, `.mergify.yml`, gate scripts).
- **P5-3 runs alone:** it removes the frontend's casts on API responses, in the same panels
  P5-1 moves onto the hook, and it regenerates the contract a Phase 4 schema change touches.
  Not at the same time as the playground lane or the backend robustness lane.
- **Free:** P2-2, P3-8, P4-4 collide with nothing above, apart from the status table of this
  page: on a conflict there, keep both ticks.

One session per lane is the limit; the owner reviews every held PR by hand, so more open
held PRs than they can read is not faster.

## Work orders

Each **Request** is the text to give `/verify`, verbatim. "Start at" names functions rather
than line numbers, which move.

### Phase 2

**P2-1. Shareable scenario link.** Done: PR #1080 (`feat/shareable-scenario-link`) is merged.
A session's only job here: act on D1's answers in a follow-up PR if the owner asks for a
change.

**P2-2. Strike Phase 2.**
- Request: `Mark Phase 2 of PLAN_GLOBAL_2026-11.md done: strike the shareable-link row with its PR number, and bring docs/STATUS.md's header and next steps up to date.`
- Branch: `docs/phase-2-done`. After #1080 merges.
- Done when: the row is struck with `#1080`; the plan's header no longer says "but for Phase
  2's shareable link"; `STATUS.md` says what shipped since v0.3.0 and what is next; every
  claim was checked against the merged PR list (`gh pr list --state merged --base polity`).

### Phase 3: correctness

Read [`LISTING_ORDER_TIES.md`](LISTING_ORDER_TIES.md) first: the invariant, the lot
(`api/engine/utils/tie_lot.py`, its twin `voter-app/src/lib/tieLot.ts`), the Fixed table and
the Open list. The test pattern for every fix: run with the candidates reversed and assert
the same result. Every engine PR regenerates the parity fixture and says, rule by rule, which
winners moved (`scripts/oracle_diff_report.py`).

**P3-1. Ranked pairs and River: equal locks by lot.**
- Request: `From LISTING_ORDER_TIES.md's Open list: the lock order of ranked pairs and River on equal margins and supports follows the names on the backend and the indices on the client. Order equal locks by the seeded lot on both engines, and keep the two engines identical.`
- Branch: `fix/ranked-pairs-river-lock-order`.
- Start at: `get_ranked_pairs_winner` and `get_river_winner` in
  `simulation_ranked_utils.py`; their twins `winRankedPairs` and `winRiver` in
  `playgroundVoting.ts`.
- Done when: a reversed-candidates test passes for both rules on both engines, on an
  electorate with two equal majorities; parity regenerated and green with `KNOWN_DIVERGENT`
  still empty; the tied-electorate snapshot of `test_compare_all_methods_snapshot.py`
  regenerated if it moved; the Open list's first bullet keeps its Kemeny half (P3-2) and
  loses the ranked pairs and River half; the Fixed table gains a row.
- Trap: the two engines must hand the lot the same names, or they draw differently on the
  same tie and the parity test fails on the draw itself.

**P3-2. Kemeny-Young: equal rankings by lot.**
- Request: `From LISTING_ORDER_TIES.md's Open list: on the exact path (up to the exact cap), Kemeny-Young's choice among equally good rankings is the name-smallest on the backend and the index-smallest on the client. Draw it by the seeded lot on both engines, and keep the two engines identical on that path.`
- Branch: `fix/kemeny-equal-rankings`. After P3-1 (same files, same fixture).
- Start at: `_kemeny_exact_winner`, `get_kemeny_young_winner` and `_KY_EXACT_CAP` on the
  backend; `KEMENY_EXACT_CAP` and `kemenyGain` in `playgroundVoting.ts`. `docs/STATUS.md`
  records Kemeny as the one ordinal rule that does not draw: change that sentence.
- Out of this work order: above the cap the two engines differ on purpose (the client falls
  back to Borda, the backend runs `_kwik_sort`), and neither computes equally good rankings
  there. `_kwik_sort` takes the middle of the candidate list as its pivot, and its caller
  sorts that list by name, so its answer follows the names: do not change it here, add it to
  the Open list as its own entry.
- Done when: a reversed-candidates test on both engines for an electorate with two equally
  good rankings, below the cap; parity regenerated and green; the Open list's first bullet
  is gone and the Fixed table gains a row.

**P3-3. Theory tally, multiwinner fallback, runners-up.**
- Request: `From LISTING_ORDER_TIES.md's Open list: the theory workers' assumption-testing winner (tally.index(max(tally))), the multiwinner completion's fallback when it has no rng (sorted by approval then name), and the runners-up the workers report (runner_up in /primary and the districts worker) still follow the listing order or the names. Draw each by the request's seed.`
- Branch: `fix/ties-theory-multiwinner-runner-up`.
- Start at: `tally.index(max(tally))` in `api/domain/theory/workers.py`; the fallback in
  `simulation_multiwinner_utils.py` (held file); `runner_up` and `general_runner_up` in
  `api/domain/election/workers.py`. `tie_lot.best` is the helper #1076 used for the same job;
  `api/tests/test_worker_tally_lot.py` is the test file to extend.
- Done when: a reversed-candidates test per site; the Open list loses the two bullets.

**P3-4. The last entries of #926.** D3 is answered (see its row).
- Request: `Settle the last entries of LISTING_ORDER_TIES.md's Open list as the owner decided: Hotelling's move order, identity voting's default groups, and the apportionment comparison that breaks a quotient tie by name on purpose. Record what is by design, change what is not, and leave the Open list empty.`
- Branch: `fix/ties-last-entries`.
- Start at: `_hotelling_worker` in `api/domain/election/workers_dynamics.py`;
  `identity_voting` in `api/domain/theory/`; `_hamilton` and the divisor methods in
  `api/domain/theory/workers.py`.
- Done when: the Open list is empty or says "by design" with the reason; a test pins each
  by-design behaviour. Then ask the owner to close #926: a PR into `polity` does not close an
  issue by itself (GitHub only does that on the default branch).

**P3-5. Truncated ballots: write down and pin what each rule does today.** No behaviour
change.
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 3: one stated convention for truncated ballots per rule. First step, with no behaviour change: for each of the 28 parity-locked rules, on both engines, establish by test what a truncated ballot and a ballot with equal ranks do today, write the table, and name every place where the two engines or two rules of one family disagree.`
- Branch: `test/truncated-ballots-as-is`.
- Start at: `_pairwise_wins` in `simulation_ranked_utils.py` (how an unranked candidate
  counts in a duel); `project_ballot` and `tie_lot.ranking` (the tail of a truncated ballot
  is ordered by a per-voter lot since #662); `ballot.truncate_at` on the client;
  `docs/spec/behaviors.md` and its `@pytest.mark.behavior` markers
  (`api/tests/test_behavior_catalogue.py` keeps them in step).
- Done when: a table in `docs/spec/` (rule, backend reading, client reading, same or not);
  one test per row that pins it; the disagreements listed as question D4 for the owner.
- Trap: writing the table from reading the code is not evidence. Each row comes from a test
  that ran.

**P3-6. Truncated ballots: one convention.** Blocked on D4, after P3-5.
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 3: one stated convention for truncated ballots per rule, one shared pairwise-defeat definition, and Hypothesis strategies with truncated and unequal ballots.`
- Branch: `fix/truncated-ballot-convention`. Likely two PRs: the shared pairwise-defeat
  definition with the rules moved onto it, then the Hypothesis strategies
  (`test_hypothesis_condorcet.py`, `test_hypothesis_monotonicity.py`,
  `test_voting_criteria_matrix.py` are where the current strategies live).
- Done when: every row of P3-5's table reads "same"; the criteria matrix still classifies
  each rule as before or the PR says which cell moved and why; parity regenerated.
- After adding or changing a rule function, run the `axiom-checker` and `parity-guardian`
  agents.

**P3-7. One electorate for both engines.** Blocked on D5.
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 3: one electorate for both sides: send the client's voters to the backend, or lock the sampler, turnout, scores and scorecard axes with a second golden fixture.`
- Branch: `feat/one-electorate` or `test/electorate-golden-fixture`, by D5.
- Start at: `sampleVoters`, `applyTurnout`, `computeScores` in `playgroundVoting.ts`; the
  backend's own sampling behind `/api` (start from `api/sockets/__init__.py` and the profile
  endpoint the playground's diagnostics call); `gen_engine_parity.py` as the model for a
  second generator. `CLAUDE.md`'s note on approval ("locked at the tally only") is the same
  gap seen from one rule.
- Done when: the same seed and settings give the same voters, turnout and scores on both
  sides, proven by a fixture test or by the request carrying the voters; `CLAUDE.md`'s
  dual-engine section updated (held).

**P3-8. Validate the three one-string UI keys.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 3: the three one-string UI keys in localStorage (theme, plain language, language) are still cast as read. Check each against its allowed values and fall back to the default.`
- Branch: `fix/ui-keys-validated`.
- Start at: `votelab_theme` and `votelab_plain` in `voter-app/src/stores/useUIStore.ts`;
  `LANG_KEY` in `voter-app/src/i18n/index.ts`; `oneOf` in `lib/persistedState.ts` (exported
  by PR #1080; before that merges it is a local `const`, so wait for it or export it).
- Done when: a junk value in each key gives the default, by test; the plan's Phase 3 bullet
  is struck.

### Phase 4: robustness (ask D6 for its place in the order)

**P4-1. Throttle the Socket.IO Monte-Carlo.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 4: throttle the Socket.IO Monte-Carlo (10,000 × 2,000 against 500 × 1,000 over HTTP, and the limiter does not cover it).`
- Branch: `fix/socket-monte-carlo-limits`.
- Start at: `api/sockets/__init__.py` (the `max(10, min(2_000, …))` clamps); the HTTP
  schemas' bounds in `api/schemas/simulations.py`; the limiter in `api/core/ratelimit.py`.
- Done when: the socket's bounds equal the HTTP ones or the PR says why not; a client that
  asks for more is clamped or refused, by test; repeated runs from one client are limited.
  Check the frontend's stream hook (`useMonteCarloStream`) still gets what it asks for.

**P4-2. Key the rate limiter on the real client address.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 4: key the rate limiter on the real client address.`
- Branch: `fix/ratelimit-client-address`. Held: `api/core/ratelimit.py`.
- Start at: `Limiter(key_func=get_remote_address)`. Behind a proxy that is the proxy's
  address.
- Done when: the key is the client's address when a trusted proxy forwards it, and a
  forwarded header from an untrusted peer is ignored (a spoofed header must not buy a fresh
  bucket), both by test. Run `/security-review` on this one.

**P4-3. A work budget and timeouts that stop the work.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 4: a per-request work budget; timeouts that stop the work.`
- Branch: `fix/work-budget-timeouts`.
- Start at: `api/core/worker_dispatch.py`. Establish first, by test, whether a timed-out
  request's worker keeps running today.
- Done when: a request over budget is refused before it starts, and a timed-out one stops
  consuming CPU, both by test.

**P4-4. A per-fiche error boundary.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 4: a per-fiche error boundary.`
- Branch: `fix/fiche-error-boundary`.
- Start at: `components/Route/ErrorBoundary.tsx`, which today wraps the whole app in
  `App.tsx`; the Laboratoire's fiche rendering.
- Done when: a fiche that throws shows its own message and a retry, the rest of the
  Laboratoire stays usable, by test; strings in FR and EN.

**P4-5. Finish #692.**
- Request: `Finish issue #692: pin images and pip installs by hash (production images are already digest-pinned).`
- Branch: `ci/pin-by-hash`. Held, and "Workflow lint" must pass (actionlint, `zizmor
  --offline`, the hooks' unit tests).
- Start at: `gh issue view 692`; every `pip install` and `image:` in `.github/workflows/`
  and the Dockerfiles.
- Done when: every `image:` carries a digest and every `pip install` in a workflow or a
  Dockerfile installs from a hashed lockfile (`--require-hashes`), or the PR lists each one
  left with its reason; "Workflow lint" passes. Then ask the owner to close #692.

### Phase 5: engineering leverage

**P5-1. One `useSimulation` hook.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 5: one useSimulation hook (cache, cancel, shared loading and error) in place of the block repeated across about 45 panels.`
- Branch: `refactor/use-simulation-hook`, then `refactor/use-simulation-batch-<n>`.
- Start at: the repeated block is the `$api.useMutation` call with its `isPending` and
  `isError` handling and a cast on `data` (`grep -rlE 'useMutation' voter-app/src
  --include='*.tsx'` gave 43 files outside tests on 2026-11-14); about ten more panels keep
  their own `setLoading(true)` state. The hook has to serve both. `hooks/usePlaygroundData.ts`
  already does part of this for the playground.
- Done when, first PR: the hook, its tests (a stale answer never overwrites a newer one; an
  unmounted panel sets no state; an error is shown and retried), and three panels moved.
  Later PRs: the rest, ten or so at a time, no behaviour change, jscpd count lowered.

**P5-2. Monte-Carlo and grid libraries in a Web Worker.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 5: the Monte-Carlo and grid libraries in a Web Worker.`
- Branch: `refactor/monte-carlo-worker`.
- Start at: `voter-app/src/workers/engine.worker.ts` (the existing worker);
  `shakeWinRates` in `lib/playgroundDynamics.ts`; `leaderScorecard` in `lib/scorecard.ts`;
  the win-region grid behind `LeaderCanvas`'s lenses.
- Done when: a candidate drag stays responsive while the scorecard computes (measure before
  and after, and put the numbers in the PR); results are identical to the main-thread ones,
  by test; the bundle stays under the 1 MB budget.

**P5-3. Typed nested API responses.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 5: typed nested API responses.`
- Branch: `refactor/typed-api-responses`. Held: the OpenAPI contract is a regenerated oracle.
- Start at: `voter-app/src/api/types.gen.ts` (generated; about 500 `unknown`); the backend
  response models that declare `dict[str, Any]`. Use the `voter-api` skill.
- Done when: the responses the frontend reads are typed end to end, the frontend's casts on
  them are gone, type-coverage does not fall; the PR lists which schemas changed.

**P5-4. Split `AVousDeJouerPage` and `LeaderCanvas`.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 5: split AVousDeJouerPage and LeaderCanvas.`
- Branches: `refactor/split-a-vous-de-jouer`, `refactor/split-leader-canvas` (two PRs).
- Done when: no behaviour change; every existing test passes untouched; the visual baselines
  do not move (a moved baseline here is a regression, not something to regenerate); testids
  unchanged. `LeaderCanvas` is memoised: `InstrumentPanel.memo.test.tsx` and
  `PlaygroundController.render.test.tsx` guard its re-renders.

### Phase 6: process diet (all held; one at a time)

**P6-1. Observers into one daily job.** Blocked on D7.
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 6: make "CI health check" advisory and fold the observer workflows into one daily job.`
- Branch: `ci/observers-daily-job`.
- Start at: `ci-health.yml`, `ci-dashboard.yml`, `branch-red-alert.yml`, `red-on-base.yml`,
  `flaky-check-backend.yml`. Use the `voter-ci` skill. Scheduled workflows run `develop`'s
  copy, so a fix is live only after a sync.
- Done when: the workflows the owner named under D7 run as one scheduled job; what each one
  reported is still reported (list them in the PR, one line each: where it shows now); no
  required status disappears without the owner having changed branch protection first;
  "Workflow lint" passes. The PR gives the count of observer runs over the last 30 days,
  before, and what the new schedule makes it.

**P6-2. Narrow the hold list.** Blocked on D7.
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 6: narrow the human-review hold list.`
- Branch: `ci/narrow-review-hold-list`.
- Start at: the `files` conditions in `.mergify.yml`; `branch-policy.yml` checks each
  pattern still matches a file. A session proposes the list with the reason for each path;
  the owner chooses.
- Done when: `.mergify.yml` holds exactly the paths the owner kept; `CLAUDE.md`'s paragraph
  on high-risk paths and this page's Held definition say the same thing; the "Review-hold
  path patterns still match files" check passes.

**P6-3. Group Dependabot's updates.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 6: group Dependabot's updates.`
- Branch: `ci/dependabot-groups`. Start at `.github/dependabot.yml`; some groups exist
  already (`patch-and-minor`). The `dep-triage` agent knows the history.
- Done when: the PR shows, from the Dependabot PRs of the last 30 days
  (`gh pr list --state all --author 'app/dependabot'`), how many there were and how many the
  new groups would have made; majors stay one PR each; the file validates (Dependabot
  reports a bad config on the PR itself).

**P6-4. The ratchet lowers its own baseline.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 6: let the quality ratchet lower its own baseline and run locally.`
- Branch: `ci/ratchet-self-lowering`. Start at `scripts/check_quality_ratchet.sh`,
  `audit.yml`'s `code-quality` job, `scripts/fast-gate.sh`.
- Done when: a PR that removes debt needs no hand edit of the baseline, and one command
  measures the counts locally. Then delete the ratchet paragraph from "Local traps" above.

**P6-5. Polity's own CI job and requirements file.** Blocked on D8. Branch:
`ci/polity-own-job`. No Request yet: the owner's answer to D8 is the request.

**P6-6. A scheduled check of the Playwright image digest.**
- Request: `From PLAN_GLOBAL_2026-11.md, Phase 1's note: the image version sync only asks the registry when a PR changes the pin, so a re-pushed tag shows on a release sync and not before. Add a scheduled advisory run that catches it early.`
- Branch: `ci/playwright-digest-watch`. Start at the "Playwright/Docker image version sync"
  job in `e2e.yml`.
- Done when: a scheduled run compares the pinned digest with the one the registry serves
  and says so when they differ, without failing any PR; the comparison is exercised once
  with a wrong digest (a dry run whose output is in the PR); "Workflow lint" passes. It runs
  from `develop`'s copy, so it is live only after a sync: say that in the PR.

### Phase 7: new features

Blocked on D9. For each, the first PR is a design note of one page in `docs/plan/vote-app/`
(what the visitor does, what is stored, what is out of scope), which the owner agrees to
before any code. `W3.5` in `docs/plan/PLAN_BEYOND_CI.md` is the existing note for class mode.

- **P7-1.** Bring your own ballots (paste, CSV, PrefLib) and export. Note:
  `docs/bring-your-own-ballots`.
- **P7-2.** Predict-then-reveal and challenges. Note: `docs/predict-then-reveal`.
- **P7-3.** Class mode. Note: `docs/class-mode`.

The note's PR is the claim. Its Request is the plan's line for that feature, and it is done
when the owner has agreed to it; the note then lists the feature's own work orders, added to
the status table above.

### R-1. Release 0.4.0

Only when every row above is `done` or the owner has struck it. Use the `release` skill. The
steps that worked for v0.3.0: a bump PR, the `polity` → `develop` sync
(`chore/sync-polity-into-develop-<date>`, a real merge commit, exempt from `/code-review`),
the `develop` → `main` release PR opened **before** the day of the release (it re-runs
diff-cover against `main` and found uncovered lines last time), the owner's merges, the
owner's go for the dispatch, then `CITATION.cff`.
