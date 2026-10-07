---
name: release
description: Checklist for a develop → main release via the "Release Vote Lab" GitHub Actions workflow — what to check before dispatching it, how to dispatch it, and what needs manual follow-up afterward. Use when preparing, dispatching, or following up on a Vote-App release.
---

# release — polity → develop → main checklist

Releases are infrequent and human-triggered, never automatic. The first real
one was **v0.2.0 (2026-09-27)**, after two tries: #669 merged, the dispatch
died in the workflow's own backend gate (fixed by #672), then #673 and a fresh
dispatch tagged it.

`polity` is the working branch (#676). `develop` only receives release syncs,
so a release has three hops: polity → develop → main → tag.

## Before dispatching

- [ ] **Bump the version in a PR to polity first.** `main` is protected (PRs
      only), so the release job no longer commits a bump: it releases whatever
      `voter-app/package.json` says on `main`, and refuses a version that is
      already tagged on another commit. Branch `chore/release-vX.Y.Z` from
      polity, run `npm version X.Y.Z --no-git-tag-version` in `voter-app/`
      with an explicit version above the latest tag
      (`git ls-remote --tags origin 'v*'`; not `patch`/`minor`, which count
      from polity's own value and polity was left at 0.1.0 while v0.2.0
      shipped), and merge it like any PR before the sync below. The release
      job refuses a version that is not above the latest tag, before CI runs.
- [ ] **Sync polity into develop.** Cut `chore/sync-polity-into-develop-<date>`
      from `origin/develop`, merge `origin/polity` (a real merge commit), and
      open a PR into `develop`. Its diff-cover gate measures every polity line
      that develop lacks, so an untested polity branch fails here even though
      it passed on polity (#674 needed five tests for that reason).
- [ ] `develop` is green: Backend CI, Frontend CI, Playwright E2E, Generated
      Artifacts Contract on its latest push.
- [ ] Know what's shipping: `git log --first-parent origin/main..origin/develop --oneline`.
- [ ] **Open the develop → main PR.** `branch-policy.yml` allows only `develop`
      as the source, and, like every PR, it needs a **Conventional Commits title**. Use
      `chore(release): <summary>`; the old `Release: …` form is rejected.
- [ ] **Expect red checks on it, and know which ones matter.** diff-cover
      compares against `main`. When `main` is far behind, it re-counts code that
      already passed diff-cover on its way into develop (#669: 55 lines). Scorecard
      can list alerts that were there before. `main` requires the base checks
      (`develop`'s minus the review gate and Workflow lint, which don't run on
      PRs to `main`), but `enforce_admins` is off, so the owner can merge over
      a red check after confirming it is one of these, never a real regression.
- [ ] **Merge it by hand.** Mergify's queue only covers PRs into `develop` and
      `polity`. A PR into `main` gets the `dequeued` label and sits there.
- [ ] **Version field:** the PR's `voter-app/package.json` must carry the new
      version. v0.2.0's bump commit was pushed straight to `main`, which says
      0.2.0 while polity and develop say 0.1.0, so the first release after this
      change may conflict there: keep the new, higher version.
- [ ] **Hold the next polity → develop sync until the tag exists.** The
      develop → main PR's head is `develop` itself, so anything merged into
      develop first ships with it.

## Dispatching

```bash
gh workflow run release.yml --ref main   # optional: -f release_notes='...'
```

Dispatch **after** the develop → main PR has merged, with `--ref main`. The
`release` job requires `main` to be **exactly** the commit the run tested.
Ancestry isn't enough, and anything else fails the job before any tag or
push. This also makes a dry run safe: dispatching on a feature branch runs the
gates, then stops at that check.

**After a failed run, dispatch a fresh one; never use "Re-run".** A re-run
replays the workflow file from the failed run's commit, including whatever bug
made it fail. It also can't pass the exact-commit check once `main` has moved.

## What happens automatically

1. The gates re-run on the tagged commit:
   - `ci-frontend`: `npm run test:coverage && npm run build`, which covers the
     coverage thresholds, tsc and the 1 MB size-limit.
   - `ci-backend`: the dev lockfile install, `pytest api/tests -n auto` from
     `fast_api_voter/`, and the engine perf ceilings.
   - `e2e`: the full `e2e.yml`, including visual regression.

   Nothing else tests this commit. Backend and Frontend CI skip their test jobs
   on pushes to `main`, because their paths filter sees no change. See #683 for
   making the release job reuse them instead of copying them.
2. Then `main` is tagged `vX.Y.Z` from `voter-app/package.json`, and only
   the tag is pushed. The `version` job checked it before CI started: above
   the latest tag, not already released. A tag on this commit with no GitHub
   Release (a dispatch whose release step failed) is reused by a fresh
   dispatch, which then creates the release.
3. A GitHub Release is created from that tag (`generate_release_notes: true`,
   `make_latest: true`).

`concurrency` is `cancel-in-progress: false`, so a second dispatch queues
behind the first instead of racing it. The queued one then fails in its
`version` job, before any CI: that version is already released.

## Afterwards

- **Confirm it landed:** `gh release list` and `git ls-remote --tags origin`.
- **The backend has no version file or tag.** The release version is
  frontend-only.
- **No deployment step exists.** The tag and GitHub Release are the whole
  release.
- **Then run the polity → develop sync you held back** (see Before dispatching).
