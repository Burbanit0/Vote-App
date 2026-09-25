---
name: voter-ci
description: Where Vote-App's CI gates actually live, job by job, how to reproduce a failure locally before pushing, what the quality ratchet is and when `--update` is legitimate, and how to pull the real error out of a red GitHub Actions check instead of guessing from the job name. Use when a PR check is red, a required check is stuck pending, the quality ratchet or diff-cover gate fails, or you need to know which workflow/job/config file is actually responsible for a given rule.
---

# voter-ci — CI gates, diagnosis, and the quality ratchet

Vote-App's CI is 15 workflow files (`.github/workflows/`). Most PRs only ever
see four of them; this skill maps every gate to its config file, explains the
two gates that most often surprise people (the quality ratchet, diff-cover's
100%-changed-lines rule), and gives the actual recipe for turning a red check
into a real error message.

## The gates, job by job

### `backend-ci-cd-pipeline.yml` — "Backend: Tests + Coverage + Security" (required)

Triggers on every push/PR to `develop`/`main` but only *runs* its real job
when `fast_api_voter/**` changed (a `changes` job with `dorny/paths-filter`
gates it — see "Why no top-level `paths:` filter" below). In order:

| Step | Tool | Gate | Config |
|---|---|---|---|
| Lockfile freshness | `bash scripts/check_python_lockfile_freshness.sh` | informational (`continue-on-error`) | see the script's own header |
| Install | `uv pip install --system -r fast_api_voter/requirements-dev.lock.txt` | blocking (install must succeed) | `fast_api_voter/requirements-dev.lock.txt` (the compiled lockfile, not `requirements*.txt` live — PLAN_CI_STRUCTURAL_GAPS.md item 2.C) |
| Ruff | `ruff check fast_api_voter` | blocking, pyflakes (`F`) only | `fast_api_voter/pyproject.toml`'s `[tool.ruff]` |
| Import layering | `lint-imports` | blocking — enforces routes→domain→engine | `[tool.importlinter]`, same file |
| Bandit | `bandit -r fast_api_voter/api -ll --skip B104,B311` | blocking, medium+ severity | inline flags |
| pip-audit | `pip-audit --requirement fast_api_voter/requirements.txt` | blocking (CVEs) | — |
| License compliance | `bash fast_api_voter/scripts/check_license_compliance.sh` | blocking, production deps only | script |
| Mypy | `python -m mypy api/ --config-file mypy.ini` | blocking, strict | `fast_api_voter/mypy.ini` |
| Tests + coverage | `pytest api/tests -n auto --cov=api --cov-fail-under=90` | blocking, 90% global floor | `pyproject.toml` addopts |
| diff-cover | see its own section below | blocking, **100% on changed lines** | — |
| Engine perf ceilings | `pytest api/tests/test_engine_benchmarks.py -o addopts=""` | blocking, generous absolute ceilings (15-500x baseline) | see `docs/exploration/EXP-006` |

### `frontend-ci-cd-pipeline.yml` — "Frontend: Tests + Coverage + Security" (required)

Same `changes`-gated shape, scoped to `voter-app/**`:

| Step | Tool | Gate | Config |
|---|---|---|---|
| Lint | `npm run lint` (`eslint . --ext .js,.jsx,.ts,.tsx`) | blocking, 0 errors | `voter-app/eslint.config.js` |
| Architecture boundaries | `npm run depcruise` | blocking | `voter-app/.dependency-cruiser.json` |
| npm audit | `npm audit --audit-level=high` | blocking, high+ CVEs | — |
| License compliance | `license-checker-rseidelsohn --production` | blocking, production deps only | inline allowlist |
| Tests + coverage | `npm run test:coverage` (`vitest run --coverage`) | reporters configured, no hard floor here | `voter-app/vitest.config.ts` |
| diff-cover | see below | blocking, **100% on changed lines** | — |
| Build | `npm run build` (`tsc --noEmit && vite build && npm run build:size`) | blocking — tsc, then Vite build, then `size-limit` (1 MB brotli budget) | `voter-app/.size-limit.json` |

### `e2e.yml` — "Playwright E2E" (required) + "Visual regression" (not yet required — see EXP-004)

Called on every PR (paths-gated the same way), on push to `develop`, and via
`workflow_call` from `release.yml`. Boots the real FastAPI backend on `:4434`
as a fixture, then `npm run test:e2e` (chromium + firefox + mobile). A
separate `visual-regression` job runs pixel-diff screenshots inside an
**exact pinned** `mcr.microsoft.com/playwright:v<X>-noble` image (`e2e.yml`
has the current tag; must match `voter-app/package.json`'s
`@playwright/test` version exactly — a mismatch fails to find the
pre-installed browsers, or worse, silently renders against a different
browser build than the one that produced the committed baselines, e.g.
PR #477's live break when a Dependabot `@playwright/test` bump landed
without this tag moving in lockstep) — never on a bare `ubuntu-latest`,
because the OS image itself can silently drift renderer output between
runs (`docs/exploration/EXP-004`). `check-flaky.mjs`
runs after the main e2e job (`if: always()`) and fails the run if any test
passed only on retry.

### `openapi-contract.yml` — "Generated artifacts in sync" (required)

Two independent generated-artifact drift checks, run back-to-back
(`if: always()` on the second so both verdicts show up in one run even if the
first fails):

```bash
./scripts/check_openapi_drift.sh          # openapi.gen.json + types.gen.ts
./scripts/check_engine_parity_drift.sh    # engineParity.json (see voter-testing skill)
```

Both regenerate-then-diff; a nonzero diff against the committed artifact is
the failure. Triggered not just by `fast_api_voter/api/**` but also by
`fast_api_voter/requirements.txt` — a dependency bump changed Pydantic's
`ValidationError` shape once (fastapi 0.121.2 → 0.141.1, PR #253) without
touching `api/**` at all, and that went uncaught until the filter started
watching requirements too.

### `audit.yml` — "Security Audit" (four required jobs, several informational)

| Job | Gate | Notes |
|---|---|---|
| Semgrep SAST | **required**, `--error` on any finding | rules in `.semgrep/vote-app-rules.yml` + `p/python`, `p/javascript`, `p/react`, `p/security-audit`, `p/secrets`, `p/sql-injection`, `p/owasp-top-ten` |
| Secret Scan (Gitleaks) | **required** | `.gitleaks.toml`; TruffleHog alongside is informational only |
| Dependencies, Containers & Misconfig (Trivy) | **required**, HIGH/CRITICAL fs scan | `.trivyignore.yaml` for triaged false positives |
| Code Quality | **required**, via two gates at the end: the ratchet, then `xenon -a A` (repo-wide average complexity must stay rank A) — see below | vulture/radon/deptry/knip/sonarjs/jscpd all run `continue-on-error: true`; only those two final steps can fail the job |
| CodeQL (`javascript-typescript`, `python`) | **required**, non-gating by itself | results land in the Security tab, not a hard fail |
| GuardDog, Docker image scan/SBOM | informational only | second opinions / supply-chain, not PR blockers |

`CodeQL` and `Semgrep`/`Gitleaks`/`Trivy` all live in this one file, not
scattered — if you're looking for "where is CodeQL configured", it's here,
not a separate `codeql.yml`.

### Other workflows — informational or off the PR path entirely

- `branch-policy.yml` — required, validates PR source-branch naming
  (`feature/`, `fix/`, … into `develop`; **only `develop`** may be the source
  of a PR into `main`).
- `dependency-review.yml` — required, fails a PR that *introduces* a
  vulnerable dependency (complements Dependabot, which only scans what's
  already there).
- `mutation-testing.yml`, `schemathesis.yml`, `flaky-check-backend.yml`,
  `atheris-fuzzing.yml` — never run on `pull_request` at all (push-to-`develop`
  + cron + `workflow_dispatch` only), deliberately not required checks
  (`scripts/setup-branch-protection.sh`'s own comment: a required check under
  a workflow that never triggers on a PR blocks that PR forever — the exact
  failure PR #205 hit). Their `schedule`/`workflow_dispatch` triggers resolve
  against GitHub's **default branch**, which used to be `main` (hundreds of
  commits behind `develop`) and made these four inert outside their
  `push: develop` trigger — **that's fixed**: the repo's default branch is
  now `develop`, confirmed by live successful runs (`flaky-check-backend.yml`'s
  cron on 2026-09-12, `atheris-fuzzing.yml`'s dispatch on 2026-09-11). See each
  workflow's own `on:` comment for the fuller history. **Being non-required is
  exactly why `mutmut` crashed on every single run for 17 days
  (2026-08-29 → 2026-09-13) unnoticed — see `ci-health.yml` below, which
  exists specifically to catch that class of rot.**
- `scorecard.yml`, `dast.yml` — informational, non-gating, results in the
  Security tab.

### Why no top-level `paths:` filter on the four required-check workflows

`backend-ci-cd-pipeline.yml`, `frontend-ci-cd-pipeline.yml`, `e2e.yml`, and
`openapi-contract.yml` all trigger unconditionally and push the actual
`paths:` scoping down into a `changes` job (`dorny/paths-filter`). This is not
an oversight — a required check scoped by `paths:` at the trigger level never
even creates a check run on a PR that doesn't touch those paths, which blocks
that PR's merge **forever** (a required check that never reports can't be
satisfied). This exact failure hit PR #205 (a docs/CI-only change). If you see
a required check stuck pending with no run at all, this is the first thing to
check — has its workflow been converted to the always-triggers-but-skips
pattern, or does it still filter at the trigger?

## The quality ratchet (`scripts/check_quality_ratchet.sh`)

`audit.yml`'s `code-quality` job runs vulture (Python dead code), radon
(cyclomatic complexity, rank C+), deptry (unused/undeclared deps), knip (TS
dead code/unused deps), sonarjs (`eslint-plugin-sonarjs`'s full recommended
ruleset, informational-only in the blocking `eslint.config.js`), and jscpd
(cross-language duplication) — all with `continue-on-error: true`, because
the repo never did a full cleanup pass and failing outright on the existing
backlog would just get the job disabled.

The ratchet is the actual gate, reading the `.txt` files those tools already
`tee`d (zero extra CI seconds):

```bash
./scripts/check_quality_ratchet.sh            # check (what CI runs)
./scripts/check_quality_ratchet.sh --update   # accept current counts as the new baseline
```

- **Debt may shrink, never grow.** It compares each tool's finding count
  against `.github/quality-baseline.json` and fails on any **increase**
  (existing debt is grandfathered) — but it *also* fails on any **decrease**,
  on purpose: a baseline nobody remembers to lower never gets lowered, and
  every uncommitted cleanup silently loosens the ratchet for the next
  regression. A `🟢` decrease is still a failing exit code, with the message
  telling you to run `--update` and commit the new baseline alongside your
  cleanup.
- **`--update` is legitimate exactly when you just shrank the debt** (fixed a
  vulture finding, removed a duplicate block, etc.) and are committing that
  fix in the same PR. **It is never legitimate as a way to make a ratchet
  failure go away without understanding why the count moved** — a `🔴`
  increase means new debt was actually added; the fix is to address the new
  finding (or silence a genuine false positive at its source —
  `.vulture_whitelist.py`, `pyproject.toml`'s `[tool.deptry]`,
  `voter-app/knip.json`, `.jscpd.json`, or for sonarjs a
  `// eslint-disable-next-line sonarjs/<rule>` comment / rule override in
  `voter-app/eslint.sonarjs.config.js`), not to launder it into the baseline.
- **Measure `--update` on an up-to-date branch.** CI runs these tools against
  the PR's merge result; the script's own header notes a real incident where a
  baseline measured one merge behind `develop` disagreed with CI by exactly
  the one finding the missing merge had added. Rebase on `develop` before
  running `--update`.
- A missing input `.txt` file is treated as a hard error, not "0 findings" —
  `require()` refuses to report a passing ratchet on data that was never
  produced (a broken install or renamed tool step would otherwise silently
  pass everything).
- A second, independent gate in the same job locks the **average** complexity
  rank at A (`xenon api/ -b F -m F -a A`) — per-block still allows F/E-ranked
  functions (9 F, 20 E existed when this was written; gating those outright
  would fail on the existing backlog), but the codebase-wide average can never
  drift worse than A.

## The mutation score ratchet (`scripts/check_mutation_score.sh`)

**Scope first, because the number invites over-reading**: the baseline score
(66.57% as of this writing) is measured over a deliberately narrow,
hand-picked file selection (`[tool.mutmut]` in `fast_api_voter/pyproject.toml`
— currently 3 backend files, ~4,700 of the repo's ~40,000 backend lines;
Stryker's frontend half is narrower still, one file,
`playgroundVoting.ts`). It is **not** a repo-wide code-quality metric, and
citing it as one (in a status update, a PR description, a dashboard) is a
plan-doc-flagged mistake — `PLAN_SURFACE_EXTERIEURE.md` §2.L. Say "the
mutation score on its current ~4%-of-the-codebase scope" or name the actual
files, not "the mutation score."

Same idiom as the quality ratchet above (`.github/mutation-baseline.json`
records `{score, killed, total}`, `--update` accepts a new one), for the
backend half of `mutation-testing.yml`. A hand-maintained percentage floor
sat in the workflow file until 2026-09-13 — nobody remembered to raise it as
the score improved, and mutmut 3.8.0's coverage-gathering fix (see that
workflow's own history and `PLAN_REMEDIATION_CI_CD.md` §2.1) made the old
number meaningless overnight anyway when the mutant population tripled.

**One deliberate difference from the quality ratchet**: this one does
**not** fail on an improvement, only on a real drop (past a small noise
tolerance). The quality ratchet's tools are fully deterministic; mutmut
has genuine run-to-run non-determinism from mutant timeouts (observed
directly — two back-to-back runs of the identical commit differed by
~0.1 percentage points with zero code change). A symmetric "fail on any
change" rule would make this gate fail on pure noise most runs — exactly
the kind of ignored-because-it-cries-wolf signal this repo's whole
`ci-health.yml` effort exists to prevent. An improvement is reported with
a suggestion to `--update`, not forced.

```bash
./scripts/check_mutation_score.sh fast_api_voter/mutmut-run.log            # check (CI)
./scripts/check_mutation_score.sh fast_api_voter/mutmut-run.log --update   # accept the current score as the new baseline
```

Same "measure on an up-to-date branch" caveat as the quality ratchet — CI
measures against the PR's merge result.

## The type-coverage ratchet (frontend, `package.json`'s `typeCoverage.atLeast`)

A third ratchet, same family, but this one needs no wrapper script: the
`type-coverage` tool (frontend, TS) has the mechanism built in natively.
`voter-app/package.json`'s `"typeCoverage": {"atLeast": <percent>}` is read
automatically by a bare `type-coverage` invocation (`npm run type-coverage`,
also the step in `frontend-ci-cd-pipeline.yml`) — no CLI flag needed — and it
fails the run if the real percentage drops below it.

Was informational-only (PLAN_SOLIDITE_TECHNIQUE.md §6.4) until Lot 14 reduced
the 238 real (non-test) implicit-`any` positions it was measuring — gating an
unreduced baseline would have meant enforcing debt, not preventing it, the
same reasoning that kept the quality/mutation ratchets from gating anything
before they had a real, reduced number to hold. Lock in a genuine future
improvement with:

```bash
cd voter-app && npx type-coverage --update-if-higher   # writes the new atLeast into package.json
```

`--update-if-higher` only ever raises the stored value (never lowers it, and
does nothing at all if `package.json` has no `typeCoverage.atLeast` key yet
to compare against) — never hand-edit the number down to make a red run
green; that's a real regression, not noise, since `type-coverage` is fully
deterministic (unlike mutmut, there's no tolerance band here).

## diff-cover — 100% coverage on changed lines

This is a *different, stricter* gate than the 90%/global coverage floor:
diff-cover only looks at lines your PR actually changed, so a large
already-tested codebase can't dilute it. Reproduce it locally before pushing:

```bash
# Backend, from fast_api_voter/ — verified working:
python -m pytest api/tests --cov-report=xml -q
diff-cover coverage.xml --compare-branch=origin/develop --fail-under=100
```

**The gotcha**: `--cov-report=xml` is not in `pyproject.toml`'s default
`addopts` (only `--cov-report=term` and `--cov-report=html` are) — you must
add it explicitly or `coverage.xml` never gets written and `diff-cover` has
nothing to read. `-o addopts=""` (CLAUDE.md's quick-local-run flag) also
works but then you lose the default coverage flags entirely and must pass
`--cov=api` yourself.

```bash
# Frontend — mirrors frontend-ci-cd-pipeline.yml exactly, including the cwd
# (test:coverage runs inside voter-app/, diff-cover itself runs from repo root):
(cd voter-app && npm run test:coverage)
# vitest writes lcov.info with SF: paths relative to voter-app/ (its own cwd),
# but git diff (and diff-cover's lcov reader) expect repo-root-relative paths:
sed 's|^SF:|SF:voter-app/|' voter-app/coverage/lcov.info > voter-app/coverage/lcov-diffcover.info
diff-cover voter-app/coverage/lcov-diffcover.info --compare-branch=origin/develop --fail-under=100
```

Both commands compare against `origin/develop` — make sure that ref is fetched
and up to date locally (`git fetch origin develop`) or the diff is computed
against a stale base and won't match what CI sees.

## `ci-local/` — the Docker mirror, and when to reach for it

`ci-local/` hand-builds Dockerfiles for four targets — `frontend`, `backend`,
`e2e`, `audit` — that reproduce the real CI environment closely enough to
catch environment-specific bugs a native run hides (its own README cites a
real Linux-only frontend coverage bug that native Windows runs never
surfaced). Run it when:

- You're about to push and want the full gating suite reproduced faithfully,
  not just the pieces you remembered to run by hand.
- A failure is suspected to be environment-specific (case-sensitive
  filesystem, Linux module resolution) rather than a real code bug.

Reach for a **real GitHub Actions log** instead when:

- The failure is already on a pushed PR — reading the actual log is faster
  than re-running the whole mirror locally.
- The workflow isn't one of the four mirrored Dockerfiles
  (`openapi-contract.yml`, `mutation-testing.yml`, `branch-policy.yml`,
  `dependency-review.yml`, `release.yml`, `scorecard.yml`) — for those, `act`
  runs the actual workflow YAML locally instead (see `ci-local/README.md`'s
  own "Beyond the 4 mirrored jobs" section), but it can't reach GitHub-native
  features (CodeQL, OpenSSF Scorecard) or steps needing a real PR's file list.
- You need to know whether a **workflow-YAML-level** bug (bad step order, a
  quoting issue in a `run:` block) is the cause, not an app bug — this is
  exactly the failure class `ci-local`'s Dockerfiles can't reproduce (they
  test the app, not the workflow file itself).

Known fidelity gaps (from `ci-local/README.md`, verify against it before
trusting a fully-green local mirror over a red PR): the local backend
coverage gate is 85%, real CI is 90%; `pip-audit` doesn't fail the local
mirror even though the real workflow gates on it; the `audit` target only
covers Semgrep/Gitleaks/filesystem-Trivy, not `image-scan`, `code-quality`,
or CodeQL.

## Diagnosing a real CI failure — the actual recipe

Never conclude from the check name alone — get the real error:

```bash
gh pr checks <pr-number>
# ...find the failing job's run/job id from the link gh prints, then:
gh api repos/{owner}/{repo}/actions/jobs/<job-id>/logs | tail -100
# equivalent, often more readable:
gh run view --job <job-id> --log-failed
```

This exact technique (and the repo's own catalogue of previously-seen failure
signatures — `uv pip install --system` resolver conflicts, `npm ci`
`ERESOLVE` peer-dependency caps, `engines.node` mismatches against this repo's
pinned Node version, currently 24) is written up in `.claude/agents/dep-triage.md` for the
Dependabot-PR case specifically; the same "get the real log, don't guess from
the job name" discipline applies to any red check, not just a dependency bump.

## `ci-health.yml` — catching a non-required workflow rotting silently

Every workflow in the two tables above that isn't a required check
(`mutation-testing.yml`, `schemathesis.yml`, `atheris-fuzzing.yml`,
`flaky-check-backend.yml`, `dast.yml`, `scorecard.yml`) rots invisibly by
construction: nothing blocks a human from ignoring a red run, because
nothing requires them to look. That's not hypothetical — `mutmut` crashed on
every single run for 17 days before anyone noticed (numpy 2.4+ vs. mutmut
3.7.0's in-process coverage model; fixed in PR #447 by bumping to 3.8.0).
The same audit that found it also found `develop`'s branch protection had
silently drifted from `scripts/setup-branch-protection.sh`.

`ci-health.yml` closes that gap with two jobs, deliberately asymmetric:

- **`audit`** (schedule + `workflow_dispatch` only, never `pull_request` —
  same reasoning as the workflows it watches) runs
  `scripts/check_ci_health.py --update`, which queries real run history for
  each watched workflow plus live branch-protection state, and opens a
  `chore/ci-health-snapshot-*` PR only when `--update`'s own `pr_needed`
  decision says so: a real status change always qualifies; a pure
  timestamp-only refresh (every workflow's `last_run_at` moves on every
  run, whether or not anything else did) only qualifies once
  `HEARTBEAT_MAX_DAYS` (7) have passed since the last snapshot commit —
  otherwise a rock-solid-healthy repo would get a trivial PR every single
  day, and a human rubber-stamping those on autopilot is worse than not
  having the check. The weekly heartbeat still exists so `verify`'s own
  staleness check never has genuinely stale-looking data to distrust on a
  repo that's simply healthy for a long stretch. That check's limit
  (`AUDIT_STALE_HOURS`) is derived from `HEARTBEAT_MAX_DAYS`, plus the wait
  for the next daily audit and time for the refresh PR to merge: it was once a
  flat 36h, which a weekly heartbeat trips on days 2-7 of every quiet week,
  turning "CI health check" red on develop and every PR (2026-09-21 onward)
  with nothing wrong. If it fails with "snapshot itself is Nh old" and `audit`
  succeeded, look for an unmerged `chore/ci-health-snapshot-*` PR first (a
  snooze cannot silence it). Three real restrictions
  shaped the rest of this job, all confirmed live rather than assumed:
  - A direct push was the original design (thought to match `release.yml`'s
    push-to-`main` pattern), but `develop`'s `required_pull_request_reviews`
    block (even at 0 required approvals) makes GitHub reject any raw push
    with "Changes must be made through a pull request" — meaning
    `release.yml`'s own direct push to `main` has the same latent bug and
    has simply never been exercised for real yet (no release has shipped).
  - `GITHUB_TOKEN` couldn't open the PR at all at first either — GitHub
    blocks Actions from creating PRs by default (`gh api repos/.../actions/
    permissions/workflow`'s `can_approve_pull_request_reviews`, confusingly
    named — it's the same flag GitHub's UI shows as "Allow GitHub Actions to
    create and approve pull requests"), enabled deliberately for this repo.
  - The job does **not** try to queue its own PR (an earlier version posted
    `@mergifyio queue` on it — Mergify refused with "Command disallowed due
    to command restrictions": letting a bot queue its own PR is exactly the
    self-merge path that restriction exists to block, correctly). A human
    reviews and queues/merges it, same as any other PR. If that goes
    unnoticed, `verify`'s own staleness check is the real backstop — every
    PR starts failing once the snapshot is older than `AUDIT_STALE_HOURS`, a
    much louder signal than one unmerged PR sitting in the list.
- **`verify`** (required, every PR, no paths filter — it's cheap enough
  that skipping it is never worth the PR #205 risk of a required check with
  no run) reads that snapshot from `develop`'s tip — not the PR branch's own
  copy, since this is metadata about the *repo's* health, not the PR's diff.
  One narrow, scoped exception: a PR from a `chore/ci-health-snapshot-*`
  branch (only ever opened by `audit` itself) reads its own copy instead —
  otherwise the PR that fixes a drift could never pass the check reporting
  that same drift, a real deadlock hit in PR #493 that needed a manual
  admin-merge override to break. Scoped to that exact branch prefix, not
  just "did this PR touch the file": an unscoped version of this exception
  would let any PR self-attest a fabricated "healthy" snapshot in its own
  diff, caught by `/code-review ultra` before it shipped. Fails if:
  - the snapshot is stale (the scheduled `audit` job has gone quiet — its
    own silence has to be as loud as any other failure it reports), or
  - any watched workflow is `unhealthy` (≥2 consecutive real failures),
    `inert` (no run within 1.5× its own cron-derived cadence), or
    `never_run`, or
  - `develop`'s live branch protection has drifted from
    `scripts/setup-branch-protection.sh`.

**`CI_HEALTH_PAT`**: the `audit` job's checkout and PR-creation steps use
this secret instead of the default `GITHUB_TOKEN`, for a reason that isn't
obvious and cost real debugging time: GitHub never triggers new workflow
runs from a commit or PR authored by `GITHUB_TOKEN` (its own built-in
anti-recursion rule). Confirmed live — a bot-authored snapshot PR (#453)
sat with zero check runs, ever, until a human-authored commit on the same
branch triggered a real run immediately. A PR whose required checks can
never run can never be merged, so without a real user identity behind it,
this job's whole PR-opening step would need a human to manually nudge every
single snapshot update — exactly the automation gap this mechanism exists
to close. `CI_HEALTH_PAT` is a fine-grained personal access token, scoped
to this repo only, with exactly three permissions: **Contents: Read and
write**, **Pull requests: Read and write**, **Administration: Read-only**
— nothing else. The third one isn't obvious either and was missed on the
first pass: `check_branch_protection_drift()` reads live branch-protection
settings (`GET .../branches/{branch}/protection`), which needs
Administration access no matter which token asks — confirmed live,
`GITHUB_TOKEN` failed this specific call with "Resource not accessible by
integration" even with every other permission declared. To (re)create the
PAT (GitHub requires an expiration on fine-grained tokens, so this needs
repeating periodically):

1. https://github.com/settings/personal-access-tokens/new → resource owner
   `Burbanit0` → repository access "Only select repositories" → `Vote-App`.
2. Repository permissions → Contents: Read and write, Pull requests: Read
   and write, Administration: Read-only. Everything else: No access.
3. Generate, then `gh secret set CI_HEALTH_PAT --repo Burbanit0/Vote-App`
   (paste the token when prompted — never commit it, never paste it into a
   chat/agent session; the token itself never needs to leave the terminal
   that runs this command).

If the audit job starts failing at "Open a PR..." with a permissions error
again, the token likely expired — recreate it the same way.

A real, known problem doesn't have to block every PR forever: add a dated
entry to `.github/ci-health-snoozes.json` (key = the workflow filename, or
`branch-protection`) with `until` (a real date, never open-ended) and
`reason`. An expired snooze reverts to blocking — it does not silently keep
passing — so a snooze is a deadline, not a permanent silencer. `--verify`
still prints snoozed findings (🟡), it just doesn't fail on them.

Tested against real and injected failures before being trusted (this
repo's own standard, per the flaky-detector/depcruise/DAST precedents): the
64.4%-below-floor mutmut score above was a real one it caught immediately
on the first live `--update`; staleness, snooze-expiry, and inert-workflow
detection were each verified against constructed fixtures
(`--snapshot`/`--snoozes` override flags exist specifically for this).

## Recipe — a PR just went red

1. `gh pr checks <n>` — which check, and is it even a real failure or a
   required check stuck on "expected" (see the no-`paths:`-filter note above)?
2. Get the real log (`gh run view --job <job-id> --log-failed`), not just the
   summary — find the actual assertion/error, not "Process completed with
   exit code 1".
3. Match it to the table above to find the owning config file
   (`pyproject.toml`, `eslint.config.js`, `mypy.ini`, `.dependency-cruiser.json`,
   `.semgrep/vote-app-rules.yml`, `.github/quality-baseline.json`, …).
4. Reproduce locally with the exact command from that section (not a
   paraphrase) before pushing a fix — diff-cover and the quality ratchet
   especially depend on flags (`--cov-report=xml`, an up-to-date
   `origin/develop`) that are easy to omit locally and then be surprised by.
5. If the fix touches `engineParity.json` or `openapi.gen.json`/`types.gen.ts`,
   regenerate them via their scripts (never hand-edit) and re-run the drift
   checks before pushing again.
