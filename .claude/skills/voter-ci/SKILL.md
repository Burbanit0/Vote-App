---
name: voter-ci
description: Where Vote-App's CI gates actually live, job by job, how to reproduce a failure locally before pushing, what the quality ratchet is and when `--update` is legitimate, and how to pull the real error out of a red GitHub Actions check instead of guessing from the job name. Use when a PR check is red, a required check is stuck pending, the quality ratchet or diff-cover gate fails, or you need to know which workflow/job/config file is actually responsible for a given rule.
---

# voter-ci — CI gates, diagnosis, and the quality ratchet

Vote-App's CI is 14 workflow files (`.github/workflows/`). Most PRs only ever
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
separate `visual-regression` job runs pixel-diff screenshots inside the
**exact pinned** `mcr.microsoft.com/playwright:v1.62.1-noble` image (kept in
lockstep with `voter-app/package.json`'s `@playwright/test` version) — never
on a bare `ubuntu-latest`, because the OS image itself can silently drift
renderer output between runs (`docs/exploration/EXP-004`). `check-flaky.mjs`
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
| Code Quality | **required**, but only via the ratchet at the end — see below | vulture/radon/xenon/deptry/knip/jscpd all run `continue-on-error: true` |
| CodeQL (`javascript-typescript`, `python`) | **required**, non-gating by itself | results land in the Security tab, not a hard fail |
| OSV-Scanner, GuardDog, Docker image scan/SBOM/signing | informational only | second opinions / supply-chain, not PR blockers |

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
  failure PR #205 hit). **Their `schedule`/`workflow_dispatch` triggers
  currently resolve against `main` as the default branch, which is ~750+
  commits behind `develop`** — until a real release lands, only their
  `push: develop` trigger actually fires; the cron/dispatch paths are
  configured but dormant. See the `release` skill.
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
dead code/unused deps), and jscpd (cross-language duplication) — all with
`continue-on-error: true`, because the repo never did a full cleanup pass and
failing outright on the existing backlog would just get the job disabled.

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
  `voter-app/knip.json`, `.jscpd.json`), not to launder it into the baseline.
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
pinned Node 20) is written up in `.claude/agents/dep-triage.md` for the
Dependabot-PR case specifically; the same "get the real log, don't guess from
the job name" discipline applies to any red check, not just a dependency bump.

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
