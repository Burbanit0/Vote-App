# ci-local — GitHub CI mirror (run before every PR)

A faithful local reproduction of the GitHub Actions pipeline, so failures surface
here instead of on the PR. It mirrors the two gating jobs:

| Local target | Mirrors workflow | Environment |
|---|---|---|
| `frontend` | `.github/workflows/frontend-ci-cd-pipeline.yml` | **Ubuntu 24.04** (= `ubuntu-latest`), **Node 20** |
| `backend`  | `.github/workflows/backend-ci-cd-pipeline.yml`  | **Python 3.11** |
| `audit`    | `.github/workflows/audit.yml`                   | **Python 3.11** + Semgrep / Gitleaks / Trivy |

Targets: `all` (default) = frontend + backend + audit (**run before each push**) ·
`code` = frontend + backend only (quick iteration) · plus the individual names.

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

**Frontend** — `npm run lint` (non-blocking, matches `continue-on-error`) →
`npm audit --audit-level=high` → `npm run test:coverage` → `npm run build`.

**Backend** — `flake8` (non-blocking) → `bandit --exit-zero` (non-blocking) →
`pip-audit` (non-blocking) → `mypy api/` (gating) →
`pytest api/tests --cov=api --cov-fail-under=30` (gating).

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

- Backend base is Debian-slim (for the exact 3.11.x interpreter); the runner is
  Ubuntu. Irrelevant for pure-Python + manylinux wheels.
- E2E (`e2e.yml`, Playwright) is **not** mirrored here — it needs both servers and
  browser downloads. Run it directly with `npm run test:e2e` when needed.
- Networked steps (`npm audit`, `pip-audit`) need internet, same as CI.
