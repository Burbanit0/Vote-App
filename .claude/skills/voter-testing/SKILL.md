---
name: voter-testing
description: How to test Vote-App — Hypothesis property-based tests on the voting engine, the client⇄backend engine-parity fixture workflow, e2e data-testid conventions, and known pitfalls carried over from real debugging sessions. Use when writing or debugging a Hypothesis/pytest/Vitest/Playwright test, regenerating the parity fixture, or investigating a flaky or newly-failing test.
---

# voter-testing — how to test Vote-App

Three layers have non-obvious, repo-specific conventions: Hypothesis property
tests on the voting engine (backend), the client⇄backend engine-parity
fixture (both sides), and Playwright e2e anchored on `data-testid`. Plain
pytest/Vitest unit tests follow ordinary practice and aren't covered here.

## Hypothesis property tests (`fast_api_voter/api/tests/test_hypothesis_*.py`, `test_voting_criteria_matrix.py`)

Three files, one shared shape:

```python
_CANDIDATES = ["A", "B", "C", "D"]
_profiles = st.lists(st.permutations(_CANDIDATES), min_size=3, max_size=12)

@settings(max_examples=200, deadline=None)
@given(_profiles)
def test_condorcet_winner_is_elected_by_schulze_copeland_and_minimax(votes): ...
```

- **Strategy shape**: `st.permutations(candidates)` over a small fixed
  candidate set, wrapped in `st.lists(..., min_size=3, max_size=12)` for the
  voter count. Full rankings, not partial ones — every method under test
  takes complete ordinal ballots.
- **`deadline=None` is load-bearing, not decoration.** Several methods here
  (Kemeny-Young, Schulze) are exponential/cubic in candidate count; a default
  Hypothesis deadline would flag them as `DeadlineExceeded` for being slow, not
  wrong. Keep `deadline=None` on any property test over these methods.
- **`assume()` skips vacuous cases**, it doesn't weaken the property:
  `test_hypothesis_condorcet.py` calls `assume(condorcet_winner is not None)`
  because the Condorcet-consistency claim is only meaningful when a Condorcet
  winner actually exists for that profile; `test_hypothesis_monotonicity.py`
  similarly `assume()`s a promotion move exists. Hypothesis discards the
  example and draws another rather than counting it as a pass.
- **`derandomize=True` + `suppress_health_check=[HealthCheck.too_slow]`** shows
  up on the heavier per-method parametrized tests in
  `test_voting_criteria_matrix.py` (e.g.
  `test_condorcet_winner_criterion_satisfied`, run once per method via
  `@pytest.mark.parametrize`) — `derandomize` keeps the same examples across
  CI runs so a red run is reproducible without a shrink phase re-run, and the
  health check is suppressed because running the same shape once per method
  legitimately takes longer than Hypothesis's default heuristic expects, not
  because anything is actually slow per-example.
- **A "can be violated" fallback test is NOT a Hypothesis `@given` test.** For
  every criterion, the methods expected to *violate* it are checked with a
  plain seeded `random.Random(f"<tag>-{method_name}")` loop (typically 20 000
  trials, 3 000 for clone independence) that returns as soon as one
  counterexample turns up, or `pytest.fail`s if none did after the full
  budget. This is deliberate, not a missed opportunity to use `@given`:
  the claim under test is an *existence* claim ("some profile violates this"),
  which Hypothesis's example-generation model isn't built to assert directly
  without a dedicated `find()`-style search — a plain seeded loop is simpler
  and the seed keeps it reproducible.
- **A discovered violation gets pinned, not left to the random search.** Once
  fuzzing finds a real counterexample, the exact ballots are hard-coded into
  their own test (e.g. `test_condorcet_loser_irv_can_be_violated`,
  `test_clone_independence_baldwin_can_be_violated`) with a docstring
  explaining what candidate count or ballot shape was needed to expose it.
  This is more reliable than trusting the generic random search to
  re-discover a rare case (some pinned counterexamples occur in as few as
  ~2-in-6500 random trials — see `test_majority_criterion_dowdall_can_be_violated`).
- **A known, mostly-closed methodology gap, documented in the file itself**
  (`test_voting_criteria_matrix.py`'s module docstring): every random-search
  helper here fixes the candidate count at exactly 4 (`_CANDS4`/`_profiles4`),
  and the `@given` tests cap at 150-200 fixed examples. A wider,
  differently-shaped search (fast-check on the client engine, Lot 4.4; a
  15 000-24 000-trial direct Python re-sweep) found real
  satisfies/violates misclassifications this file's own narrower search
  missed — e.g. `baldwin` fails clone independence only at n=6, `dowdall`
  fails majority only on an exact-score tie. **Treat a "satisfies" cell in
  `METHODS`'s criterion sets as "not yet disproven at this search width", not
  as a permanent guarantee** — a 200-example pass at n=4 answers a true but
  narrower question than "for all profiles".
- **What a shrunk failure looks like, verified on this repo's pinned
  Hypothesis (6.167.1) by injecting a real one-token bug into
  `get_plurality_winner` and reverting it afterward.** The failure ends with
  a `Failing test case: test_xxx(votes=,)` block — on this Hypothesis/pytest
  combination that value slot reliably renders **blank**, which is a real,
  reproducible quirk of this version pairing, not a sign the shrink failed.
  The actually-useful minimized input is one screen higher, in pytest's own
  traceback local-variable dump right above the failing `assert` line, e.g.:
  ```
  votes = [['A', 'B', 'C', 'D'], ['A', 'B', 'C', 'D'], ['B', 'A', 'C', 'D']]
      def _check_monotone(votes, rule):
  >       assert rule(promoted_votes) == winner
  ```
  Shrinking did run (this is a genuinely minimal 3-ballot counterexample, not
  the raw generated one) — read the local-variable line, not the "Failing
  test case" summary, to get the concrete failing profile.

### Schemathesis contract fuzzing — two more Hypothesis gotchas

`fast_api_voter/api/tests/test_schema_contract.py` is Hypothesis under the
hood (via `schemathesis`) and documents two reproducibility traps worth
knowing even outside that file:

- **`@settings(derandomize=True)` alone is not cross-process reproducible.**
  Confirmed live in this repo (lines ~84-93): two separate local `pytest`
  invocations of the same code produced different generated examples, because
  Hypothesis's own derandomize seed derivation depends on Python's per-process
  `hash()` randomization (`PYTHONHASHSEED` unset by default). The fix that
  actually pins the sequence is an **explicit integer `seed=`** on the
  `schemathesis.Config`/`@settings` — it bypasses `hash()` entirely. This is
  the same root cause `gen_engine_parity.py` documents for
  `PYTHONHASHSEED=0` (see below) — Vote-App has hit this class of bug twice.
- **`try/except` cannot suppress a Hypothesis-internal failure.** Wrapping
  `case.validate_response()` in `try/except Exception` to silence a
  known-flaky operation reproducibly did **not** work (lines ~223-229) — the
  failure raises through Hypothesis's own engine
  (`hypothesis/core.py`'s `the_error_hypothesis_found`), which surfaces
  regardless of caller-side exception handling. The only pattern that actually
  suppresses a known failure is skipping the call to the validating method
  entirely (call-and-log, never call-and-validate) for that operation.

## The engine-parity fixture workflow

Two implementations of the voting rules — client
(`voter-app/src/lib/playgroundVoting.ts`) and backend
(`fast_api_voter/api/engine/utils/simulation_ranked_utils.py` +
`simulation_score_utils.py`) — are locked together by a golden fixture. See
CLAUDE.md's "dual voting engine" section for the invariant; this is the
day-to-day mechanics.

```bash
# Regenerate the fixture — PYTHONHASHSEED=0 is required, the script refuses
# to run without it (see gen_engine_parity.py's own comment: Python's
# per-process string-hash randomization changes tie-detection iteration
# order, which reshuffles the whole downstream RNG stream — the exact same
# class of bug as the Schemathesis seed/derandomize gotcha above).
PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py

# Or the CI-faithful path, which sets PYTHONHASHSEED for you and fails on
# any diff against the committed fixture (this is the actual "Generated
# artifacts in sync" gate — see the voter-ci skill):
./scripts/check_engine_parity_drift.sh

# Then assert the client against the (possibly regenerated) fixture:
cd voter-app && npx vitest run src/lib/playgroundVoting.parity.test.ts
```

- **Never hand-edit `voter-app/src/lib/__fixtures__/engineParity.json`** —
  it's a generated artifact. `.claude/settings.json`'s `PreToolUse` hook
  blocks any Edit/Write/MultiEdit targeting it outright.
- **The `condorcet` → `get_copeland_winner` naming mismatch.** `gen_engine_parity.py`'s
  `RULES` dict maps the client's `'condorcet'` rule id — labelled
  "Condorcet (Copeland)" in `RULE_LABELS`, and which always resolves to a
  winner — to backend `get_copeland_winner`, **not** `get_condorcet_winner`
  (the strict `Optional[str]` criterion function, often `None`). If you're
  grepping for "condorcet" in the backend expecting the literal function name
  to be the parity twin, this is the trap; the comment directly above `RULES`
  in that file documents why (every scenario that used to compare against the
  wrong function happened to have a real Condorcet winner, masking the bug
  until an exhaustive small-profile check covered cases with none).
- **`playgroundVoting.parity.test.ts` has three independent describe blocks**:
  ~590 random "strict" scenarios (winners that survive 200 candidate-relabel +
  ballot-shuffle trials — see `strict_winner`/`strict_winner_cardinal` in the
  generator — so a mismatch is never a tie-break artifact), an **exhaustive**
  domain of all 481 profiles for n≤3 candidates / m≤5 voters (a proof over
  that bounded domain, not a sample — this is where 4 of 5 real historical
  bugs were caught, because it doesn't filter out tied/degenerate cases the
  way the strict-winner scenarios do), and cardinal rules (score, STAR,
  cumulative, maximin, nash) over a shared score matrix.
- **`KNOWN_DIVERGENT` is currently empty and should stay that way.** A parity
  break is a bug until proven otherwise (CLAUDE.md); the only legitimate way
  to add to this set is a genuine, documented modeling difference (the
  pattern already used to exclude approval/majority-judgment from the
  cardinal comparison entirely, for stated reasons in `gen_engine_parity.py`
  — different ballot derivation / grade quantization, not an algorithm gap).
- For the full triage playbook on an actual divergence (map the failing rule
  id to both implementations, read the concrete failing scenario by index,
  find the specific code difference), use the `parity-guardian` agent
  (`.claude/agents/parity-guardian.md`) rather than re-deriving the process —
  it's the same steps, already written down and tool-restricted to
  investigation only (never edits the engine or the fixture).

## e2e — anchor on `data-testid`, never CSS classes or translated strings

CLAUDE.md states the rule; this is what it looks like in a real spec.

- **Routes are data**: `voter-app/src/routes.ts` (`SURFACES`,
  `LEGACY_REDIRECTS`) is read directly by `tests/e2e/routes.ts`, which pairs
  every surface with the `data-testid` that proves it rendered:

  ```ts
  export const ANCHORS: Record<Surface, string> = {
    '/': '[data-tour="hero"]',
    '/playground': '[data-testid="playground-page"]',
    '/laboratoire': '[data-testid="lab-family-rail"]',
    // ...
  };
  ```

  `assertEverySurfaceAnchored()` throws if a route added to `src/routes.ts`
  has no entry here — a new surface with no anchor fails the run instead of
  silently going untested.
- **Real spec pattern** (`voter-app/tests/e2e/playground-method.spec.ts`):
  locate by exact testid, by prefix (`[data-testid^="rule-check-"]` to select
  every checkbox in a dynamic list), assert visibility/count/attribute rather
  than text content:

  ```ts
  await page.locator('[data-testid="rules-select-all"]').click();
  const rows = page.locator('[data-testid^="replay-row-"]');
  await expect(rows).toHaveCount(total);
  await expect(page.locator(`[data-testid="lens-${lens}"]`)).toHaveAttribute('aria-checked', 'true');
  ```

  Tests run in `fr-FR` locale (pinned in the Playwright config) precisely so
  a testid-only suite can't quietly regress into matching French copy instead.
- **Local run**: start the backend first (`uvicorn api.main:app --port 4434`
  in `fast_api_voter/`), then `npm run test:e2e` from `voter-app/` — Playwright
  starts the frontend itself. Only Assemblée mode and two Laboratoire fiches
  actually call the backend; everything else is a fixture-free render.
- **A test that only passes on retry is not green.** `e2e.yml` runs
  `node scripts/check-flaky.mjs` after the suite (`if: always()`), which fails
  the job if Playwright's own retry+flaky reporting shows any test that needed
  a second attempt.

## Known pitfalls (real, from this repo's own sessions)

- **A project-level `testIgnore`/`testMatch` REPLACES the root-level one for
  that project — it does not add to it** (`docs/exploration/EXP-004`, pitfall
  5). `visual.spec.ts` was excluded via a root `testIgnore` in
  `playwright.config.ts`; once another change added a *project*-level
  `testIgnore` (for `mobile.spec.ts`) on `chromium`/`firefox`, the root
  exclusion silently stopped applying for those projects — the default suite
  ran 241 tests instead of 227, executing the visual suite against the wrong
  (unpinned) renderer. Fixed by merging every exclusion into one shared
  pattern applied per-project, not at the root. **After any change to
  `playwright.config.ts` — including a routine rebase that touches it — replay
  `npx playwright test` (no `--config`) and check the total test count**; a
  clean rebase (no merge conflict) proves nothing about runtime test-selection
  behavior.
- **React's `<Profiler onRender>` only measures the render/commit phase, never
  a passive effect's body** (`docs/exploration/EXP-005`). A 20-million-iteration
  loop hidden inside a `useEffect` produced **zero** visible change in
  `actualDuration` even though real wall-clock time increased measurably. Any
  perf assertion built on Profiler data (see `PlaygroundPage.perf.test.tsx`)
  must target work that happens during render/mount, not inside an effect —
  it is a structural blind spot, not a tuning problem.
- **An absolute-millisecond threshold on a React render is a trap even
  same-machine, same-code** (`docs/exploration/EXP-005`): a ×4.5 duration
  spread was measured between a cold and a warmed-up run of the *literal same
  unchanged code*, purely from JIT/module-loading noise in the test worker.
  This is why `PlaygroundPage.perf.test.tsx` asserts commit **count** and a
  **relative** cost ratio (heavy lens vs. a trivial toggle) instead of an
  absolute duration ceiling.
- **A shell pipeline ending in `| tail` (or any filter) masks the exit code of
  the command you meant to check** (`docs/exploration/EXP-005`): `$?` reflects
  the last element of the pipe, not the earlier command. A regression that
  really did fail the gate looked, at first, like it hadn't — check `$?`
  immediately after the command you care about, with nothing piped after it.
- **A Dockerized test runner without `--user` leaves root-owned files in the
  working tree** (`docs/exploration/EXP-004`, pitfall 6): `scripts/test-visual-docker.sh`
  ran `npm ci` as root inside the container, silently writing `node_modules/`,
  `build/`, and the Playwright report as root on the bind-mounted host
  directory — invisible until the *next* command run as a normal user failed
  with `EACCES`. Fixed with `--user "$(id -u):$(id -g)" -e HOME=/tmp`.

## Recipe — after changing a voting rule on either side

1. Change the rule in `playgroundVoting.ts` (client) or
   `simulation_ranked_utils.py`/`simulation_score_utils.py` (backend).
2. `PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py`, then
   check `git diff --stat -- voter-app/src/lib/__fixtures__/engineParity.json`
   — any diff means the backend's behavior actually moved.
3. `cd voter-app && npx vitest run src/lib/playgroundVoting.parity.test.ts` —
   must stay green (or invoke `parity-guardian` to do steps 2-3 and explain
   any real divergence).
4. If the rule is one of the 21 ordinal methods in `test_voting_criteria_matrix.py`'s
   `METHODS` registry, re-run its axiom rows
   (`python -m pytest fast_api_voter/api/tests/test_voting_criteria_matrix.py -k <method> -o addopts=""`)
   — a rule that becomes more or less "well-behaved" than its documented
   satisfies/violates classification is a correctness signal, not noise.
5. Commit the regenerated fixture together with the rule change — never
   separately, and never hand-edited.
