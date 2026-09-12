---
name: release
description: Checklist for a develop → main release via the "Release Vote Lab" GitHub Actions workflow — what to check before dispatching it, how to dispatch it, and what needs manual follow-up afterward. Use when preparing, dispatching, or following up on a Vote-App release.
---

# release — develop → main checklist

Releases are infrequent and human-triggered, never automatic. As of
2026-09-11 `main` is 750+ commits behind `develop`
(`git log origin/develop..origin/main --oneline`), no git tag exists on this
repo yet, and `voter-app/package.json`'s version has never moved past its
default `0.1.0` — the automated tag/bump mechanism below is real but
genuinely unexercised. Verify each step actually happens rather than assuming
prior runs proved it out.

## Before dispatching

- [ ] `develop` is green — check the four required checks on `develop`'s
      latest push in the Actions tab (Backend CI, Frontend CI, Playwright
      E2E, Generated Artifacts Contract).
- [ ] Know what's shipping: `git log origin/main..origin/develop --oneline`
      lists everything this release will bring in.
- [ ] Open a PR from `develop` into `main` (past convention: title
      `Release: <one-line summary>`, see merged PRs #57/#67/#70) and merge
      it. `branch-policy.yml` enforces that `develop` is the only allowed
      source for a PR into `main`. **Watch for a conflict on
      `voter-app/package.json`'s `version` field** once this workflow has run
      at least once: the release job's version-bump commit (below) lands only
      on `main` and is never merged back into `develop`, so a future
      develop→main PR could show a diff there — take `develop`'s value, the
      release workflow bumps it again regardless.

## Dispatching

```bash
gh workflow run release.yml --ref main -f version_type=patch   # or minor / major
```

Or via the UI: Actions → "🚀 Release Vote Lab" → Run workflow → pick
`patch`/`minor`/`major`, optionally fill `release_notes` (GitHub
auto-generates its own changelog from commits if left blank). Dispatch
against `main`, **after** the develop→main PR above has merged: the
workflow's `release` job checks out `main` explicitly no matter which ref you
dispatch from, and it does **not** merge `develop` itself — it only bumps,
tags, and pushes whatever is already sitting on `main`.

## What happens automatically

1. `ci-frontend` (`npm test`), `ci-backend` (`pytest`), and `e2e` (the full
   `e2e.yml`, Playwright included) all re-run and must pass before anything
   is tagged.
2. Only then: `voter-app/package.json`'s version is bumped
   (`npm version <type> --no-git-tag-version`), committed
   (`chore: bump to vX.Y.Z [skip ci]`), tagged (`vX.Y.Z`), and pushed to
   `main`.
3. A GitHub Release is created from that tag (`generate_release_notes: true`,
   `make_latest: true`).

`concurrency` on this workflow is `cancel-in-progress: false` on purpose — a
second accidental dispatch queues behind the first instead of racing it
mid-tag-push.

## What needs manual follow-up

- **The backend has no version file or tag** — nothing under
  `fast_api_voter/` is bumped; the release version is a frontend-only concept
  in this workflow.
- **No deployment step exists** in `release.yml` or anywhere else in
  `.github/workflows/` — creating the tag and GitHub Release *is* the entire
  release. Shipping it anywhere is a separate, unautomated action if one is
  needed.
- **Confirm it actually landed**: `gh release list` and `git tag -l` should
  show the new tag; if the `release` job never ran, check that `ci-frontend`/
  `ci-backend`/`e2e` all actually passed first — they gate it.
- **A first real release wakes up several currently-dormant scheduled
  workflows**: `mutation-testing.yml`, `schemathesis.yml`,
  `flaky-check-backend.yml`, and `atheris-fuzzing.yml` all resolve their
  `schedule`/`workflow_dispatch` triggers against the **default branch**
  (`main`); while `main` sits hundreds of commits behind `develop` those
  triggers are configured but inert. Once a release brings `main` current,
  don't be surprised if one of their next cron runs reports a real finding
  that had no prior chance to surface.
