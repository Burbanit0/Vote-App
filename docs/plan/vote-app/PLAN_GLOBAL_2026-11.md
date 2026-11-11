# PLAN — Vote Lab, global plan (November 2026)

> **status:** live. Written 2026-11-11 from a four-part audit of `polity` at `aa2670fb`
> (product and UX, frontend engineering, backend, process) and the ten open issues.
> Phases 0 and 1 are being executed; the rest waits for the owner's order. Polity is out
> of scope here: it has its own plans. (`docs/README.md` lists every plan.)

## Why this plan

The voting engine is the strong part: 28 rules parity-locked across two engines, a criteria
matrix, property tests, mutation testing. What is weak is the last mile. The app is not
reachable (no release since v0.2.0 on 2026-09-27, the static site not live, 0 stars and 0
forks), a few correctness gaps sit outside the locked tally, and the process around the code
has grown larger than a solo project needs.

The audit was static reading only: nothing was built or run. Every claim below was spot-checked
against the code before it went in, but a size or a cost marked *(est.)* is an estimate.

## Open issues, reconciled (2026-11-11)

| Issue | What | State on `polity` |
|---|---|---|
| #690, #691, #694 | pip in the image; workflow permissions; image-scan on `polity` | Fixed on `polity`; to close |
| #681 | the nightly flaky check hides 28 failing benchmark tests | Phase 0 |
| #682 | the 90% floor passes from 89.5% | Phase 0 |
| #683 | the release reuses Backend/Frontend CI instead of hand-copied jobs | Phase 1 |
| #692 | pin images and pip installs by hash | Half done (production images are digest-pinned); Phase 4 |
| #926 | ties still break by name or listing order | Phase 3 |
| #833, #773 | bot issues (zizmor findings; weekly CI report) | #833: Phase 0; #773 feeds Phase 6 |

## Phase 0: housekeeping

A box is ticked when the change is on `polity`.

- [ ] Close #690, #691, #694: all three are fixed (checked 2026-11-11), the issues are still
  open. #681, #682 and #683 are fixed too and also still open: their PRs said "Closes", but
  GitHub only acts on that for a PR into the default branch (`develop`), and these went into
  `polity`. They have to be closed by hand.
- [x] #682: `precision = 2` (#1041).
- [x] #681: the flaky check ignores the benchmark suite (#1041).
- [x] #833: two pinned actions carried the wrong version comment (#1041).
- [x] The live diagnostics refetch on every input the request sends: turnout, the composed
  electorate and a candidate's depth were missing from the key (#1043, with the hook's
  first test).
- [x] This page and `docs/STATUS.md` (#1045).

## Phase 1: ship what exists

- [x] #683: `release.yml` calls Backend and Frontend CI instead of hand-copied jobs (#1044).
  Not yet exercised: a release dispatch cannot run before a version bump reaches `main`.
- [x] `scripts/fast-gate.sh` works on macOS, or fails loudly. It printed "nothing to check"
  because `mapfile` needs bash 4, which is a false pass (#1042).
- [x] The `polity` → `develop` sync (#1021, merged 2026-11-11): `develop` has everything
  `polity` had. It was red on the image version sync because Microsoft re-pushed the
  `v1.64.1-noble` tag after our pin; #1046 pinned the digest the registry serves now. That
  check only asks the registry when a PR changes the pin, so the next re-pushed tag will
  again show on a release sync and not before (a scheduled advisory run would catch it early:
  Phase 6).
- [ ] Cut a release: a version-bump PR into `polity` first (it has to ride the sync, and the
  last sync went without one, so the bump needs another), then the sync, develop → main, and
  the dispatch (see the `release` skill). The static site is built and tested but only goes
  live with a release: v0.2.0 predates it, so Pages serves the CI dashboard alone.
- [x] Branch model: **kept as it is** (decided by the owner, 2026-11-11): `polity` is the
  working branch, `develop` receives the syncs, `main` is the release. `develop` stays the
  GitHub default branch, so scheduled workflows run its copy: that is why a sync has to land
  before a workflow fix is live there.

## Phase 2: product basics

| Item | Size | Builds on |
|---|---|---|
| Candidate editor: add, remove, rename, click the map to add an entrant | small–medium | the entrant-zone overlay; `setConfig({ candidates })` |
| Shareable scenario link (config, playground, rule, moment, lens in the URL) | medium | the story `Snapshot` shape |
| The sincerity result inside the Stratégie moment, so the "Vous" marker has an effect | small | `SincerityModule`, now mounted only in the Lab |
| A "why" sentence under the winner strip, and a flip sentence after a drag | small | `explainWinner`, used only in Bilan today |
| Lab search; a "reads your electorate" flag per fiche; hide Compare where it does nothing | small | the Lexique search pattern |
| First visit: the home example carries into the playground and does not overwrite saved candidates | small | `HomePage.tsx`, `applyScenario` |
| Make Beginner/Expert real, and finish plain-language names (10 of 29 rules) | medium | `useVotingLabels` |

## Phase 3: correctness

- #926 as one PR across both engines, parity fixture regenerated, and the tie lot's seed
  parity fixed with it. High-risk path: it needs the owner's `/reviewed`.
- One stated convention for truncated ballots per rule, one shared pairwise-defeat definition,
  and Hypothesis strategies with truncated and unequal ballots.
- One electorate for both sides: send the client's voters to the backend, or lock the sampler,
  turnout, scores and scorecard axes with a second golden fixture.
- Versioned, validated localStorage (`loadConfig` casts whatever it finds).

## Phase 4: robustness, needed before the API is hosted

Throttle the Socket.IO Monte-Carlo (10,000 × 2,000 against 500 × 1,000 over HTTP, and the
limiter does not cover it); key the rate limiter on the real client address; a per-request
work budget; timeouts that stop the work; a per-fiche error boundary; finish #692. Not urgent
while only the static site is public.

## Phase 5: engineering leverage

One `useSimulation` hook (cache, cancel, shared loading and error) in place of the block
repeated across about 45 panels; the Monte-Carlo and grid libraries in a Web Worker; typed
nested API responses; split `AVousDeJouerPage` and `LeaderCanvas`.

## Phase 6: process diet

Make "CI health check" advisory and fold the observer workflows into one daily job (about 40%
of runs in the last 30 days were observers); narrow the human-review hold list; group
Dependabot's updates; let the quality ratchet lower its own baseline and run locally; give
Polity its own CI job and requirements file.

## Phase 7: new features

Bring your own ballots (paste, CSV, PrefLib) and export; predict-then-reveal and challenges;
class mode (W3.5, already in `PLAN_BEYOND_CI.md`).
