# ci-local — GitHub CI mirror (run before every PR)

A faithful local reproduction of the GitHub Actions pipeline, so failures surface
here instead of on the PR. It mirrors the gating jobs:

| Local target | Mirrors workflow | Environment |
|---|---|---|
| `frontend` | `.github/workflows/frontend-ci-cd-pipeline.yml` | **Ubuntu 24.04** (= `ubuntu-latest`), **Node 20** |
| `backend`  | `.github/workflows/backend-ci-cd-pipeline.yml`  | **Python 3.14** |
| `e2e`      | `.github/workflows/e2e.yml`                     | **Python 3.14** + **Node 20** + Playwright (chromium + firefox) |
| `audit`    | `.github/workflows/audit.yml`                   | **Python 3.14** + Semgrep / Gitleaks / Trivy |

Targets: `all` (default) = frontend + backend + e2e + audit (**run before each push**) ·
`code` = frontend + backend only (quick iteration, skips the ~6 min e2e) · plus the
individual names.

`e2e` runs both sides in one container, like the workflow does on one runner: it
boots uvicorn on `:4434` as a fixture (Assemblée mode and two Laboratoire fiches
call it), then Playwright starts the vite server itself. It has been gating on
every PR since #170 — before that it ran only at release, which is how the suite
managed to rot against a UI that had moved on for two months.

## Why Docker and not just `npm`/`pytest` on Windows

The frontend coverage bug that kept reaching CI was **Linux-only**: it depended on a
case-sensitive filesystem and the Linux module-fetch path. Running tests natively on
Windows — or even bind-mounting the Windows checkout into a Linux container — hid it.
This harness **copies the source into a native Linux filesystem** and runs `npm ci`
from the committed lockfile, exactly like the runner. That is the whole point.

## Usage

From anywhere in the repo (Docker Desktop must be running):

```powershell
# PowerShell (Windows)
./ci-local/run-ci.ps1                  # both jobs
./ci-local/run-ci.ps1 -Target frontend
./ci-local/run-ci.ps1 -Target backend
./ci-local/run-ci.ps1 -NoCache         # clean rebuild
```

```bash
# bash / git-bash / WSL
ci-local/run-ci.sh                     # both jobs
ci-local/run-ci.sh frontend
ci-local/run-ci.sh --no-cache
```

Exit code is non-zero if any job fails, and a `PASS/FAIL` summary is printed. The CI
checks run as the container's `CMD`, so `docker run` failing == the PR failing.

## What each job runs (in order)

**Frontend** — `npm run lint` (gating — 0 errors) → `npm audit --audit-level=high`
(gating on high/critical) → `npm run test:coverage` → `npm run build`. All four
steps are blocking, matching the workflow (lint lost its `continue-on-error` once
it reached 0 errors).

**Backend** — `flake8 --config=fast_api_voter/.flake8` (gating; scoped to `E9,F`
— syntax + pyflakes only) → `bandit -r fast_api_voter/api -ll --skip B104,B311`
(gating on medium+ severity — the `-ll` flag itself excludes low-severity findings,
of which there are currently ~2,892, from failing the build; no `--exit-zero`) →
`pip-audit` (non-blocking **in this local mirror only** — the actual GitHub
workflow removed pip-audit's `continue-on-error` and now gates on it too; the
local Dockerfile still swallows its failure for offline/flaky-network runs, a
known fidelity gap) → `mypy api/` (gating) →
`pytest api/tests --cov=api --cov-fail-under=85` (gating; the GitHub workflow and
pre-commit hook both gate at 90% — see Fidelity caveats).

**Audit** (strict) — `Semgrep` SAST → `Trivy` deps/containers/misconfig → `Gitleaks`
secrets. **All three GATE**: any Semgrep finding, Trivy HIGH/CRITICAL, or secret fails
the run. The repo was triaged to strict-clean first; triaged false positives live in
`.gitleaksignore` + `.trivyignore.yaml` (path-scoped), so only NEW problems break it.
First build is slower (it installs the three scanners); cached afterwards.

## Performance

First build downloads the base images and runs `npm ci` / `pip install` (a few
minutes). Both are cached in their own layer, so later runs only re-copy source and
re-run the checks. Use `-NoCache` to force a clean install (e.g. after a lockfile
change you want to validate from scratch).

## Tracked-content guard

GitHub checks out only git-**tracked** files; the images COPY the working tree. A
source file on disk that git doesn't track (untracked or gitignored) is absent on
CI → "passes locally, fails on PR". Both runners run a preflight that **fails loudly**
if any `.ts/.tsx/.js/.jsx/.py` under `voter-app/src` or `fast_api_voter/api` is
untracked/ignored. (This caught nothing in the end only because it was *added after*
the `src/lib/utils.ts` gitignore bug it was designed to prevent — commit before you
validate, or it can't help.)

## Fidelity caveats

- Backend base is Debian-slim (for the exact 3.14.x interpreter); the runner is
  Ubuntu. Irrelevant for pure-Python + manylinux wheels.
- E2E downloads ~400 MB of browsers on the first build (cached with the lockfile
  layer afterwards) and takes ~6 min to run — hence `code` for quick iteration.
  Its Python 3.14 backend is a fixture, not the job under test.
- Networked steps (`npm audit`, `pip-audit`) need internet, same as CI.
- Backend coverage gate: this mirror runs `--cov-fail-under=85`; the actual
  GitHub workflow (and the repo's own pre-commit hook) gate at 90%. Measured
  coverage is currently ~91%, comfortably above both, but a change that drops
  coverage into the 85–90% band would pass here and fail on the PR.
- `audit.yml` now has more jobs than this `audit` target reproduces: this
  mirror covers Semgrep, Gitleaks and the filesystem Trivy scan only. It does
  **not** run the `image-scan` job (Trivy image scan + SBOM on the two prod
  Dockerfiles — schedule/`push`-to-`develop` only, non-gating for now), the
  `code-quality` job (vulture/knip/jscpd/radon behind a ratchet — see
  `.github/quality-baseline.json`), or CodeQL (GitHub-native, not runnable
  locally).
