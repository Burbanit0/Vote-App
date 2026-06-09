# ci-local — GitHub CI mirror (run before every PR)

A faithful local reproduction of the GitHub Actions pipeline, so failures surface
here instead of on the PR. It mirrors the two gating jobs:

| Local target | Mirrors workflow | Environment |
|---|---|---|
| `frontend` | `.github/workflows/frontend-ci-cd-pipeline.yml` | **Ubuntu 24.04** (= `ubuntu-latest`), **Node 20** |
| `backend`  | `.github/workflows/backend-ci-cd-pipeline.yml`  | **Python 3.11** |

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

## Performance

First build downloads the base images and runs `npm ci` / `pip install` (a few
minutes). Both are cached in their own layer, so later runs only re-copy source and
re-run the checks. Use `-NoCache` to force a clean install (e.g. after a lockfile
change you want to validate from scratch).

## Fidelity caveats

- Backend base is Debian-slim (for the exact 3.11.x interpreter); the runner is
  Ubuntu. Irrelevant for pure-Python + manylinux wheels.
- E2E (`e2e.yml`, Playwright) is **not** mirrored here — it needs both servers and
  browser downloads. Run it directly with `npm run test:e2e` when needed.
- Networked steps (`npm audit`, `pip-audit`) need internet, same as CI.
