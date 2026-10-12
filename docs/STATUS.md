# Status

> Where each part of the project stands and what comes next. One page, updated at
> the end of each phase of [`PLAN_BEYOND_CI.md`](plan/PLAN_BEYOND_CI.md) and whenever
> the next steps change. Last update: **2026-10-10**: W6's memo is written and waits on
> your decision (EXP-023, #908); W3.6 is done (#903, #906); W1.4 is done but for the
> outreach (#899, #900).

## The three parts

| Part | State | Plan workstream |
|---|---|---|
| **Vote Lab** (the teaching app) | 29 methods, 14 stories, 63 Lab fiches, with 28 methods parity-locked across the two engines. Merged: the paradox story's Condorcet claim, nine criteria cells and several THEORY.md statements (#859); the playground's quick fixes (#860); two more story figures caught by the new claims checks (#868); a winner strip on every playground step, five methods by default, and "no fixed winner" for the lottery (#874); a "report a content error" form and an e2e winner oracle for the stories (#875); the Bilan says why each winner wins and why two methods disagree (#885); on a phone, a story's narration and the map stay on screen together (#883). **Ties no longer follow the order the candidates are listed in** (W5): the score rules draw a tie by a seeded lot, the same on both engines (#667, #887); a voter's own tie, their nearest option and their favourite are drawn per voter (#662, #890; #663 and #665, #894); campaign and information noise follow the candidate, not its slot (#664, #895). One registry for the criteria matrix, checked by both engines (#869); each matrix cell says what its verdict rests on, with a "report a content error" link (#899); a review packet for one social-choice researcher (#900). **Results a screen reader can follow** (W3.6): the winner is announced, both maps are described, and the hemicycle's label carries the seats (#903). On a phone, every playground, navbar and matrix control is at least 44 px, and the maps' handles take a finger-sized touch (#906). Phone drag jank, measured with the CPU throttled 4×: no blocking work during a drag (`npm run measure:jank`). **Hosting** (W6): the backend engine runs in the browser through Pyodide, with the same results as on the server, at 11.9 MB on a first visit and about 2 s of startup per visit; the Fly container saturates near one request per second ([EXP-023](exploration/EXP-023-pyodide-web-worker-vs-fly-container.md), #908). | W1, W3, W5 |
| **Polity** (LLM-society research) | **The threshold experiment stops at its gate.** Told the seat threshold is 3% or 7%, founders found a party 59 times in 60 either way (exact McNemar p = 1), and at least 13 of the 14 whose backing is below 7 founded at 7% (OBS-045). By the plan's rule there is no pilot, no main run and no pre-registration, and Polity's Phase 2–3 time went to the write-up: the `docs/stories/` piece on the logprob instrument (W2.6). The instrumentation stays merged (#861–#866). The phase11 ensemble is analysed (OBS-044, #876): with OBS-041–043 fixed, turnout recovers to about 85%, and fragmentation stays (4 of 10 seeds in the 1.5–8 band at the last election). Phase 4's exit is restated (D11, 2026-10-10): the band is reported, not gated, and the exit asks the polity to respond to its fragmentation, which phase11 meets (4 of 10 seeds ratify an amendment to party entry or seats). | W2 |
| **Process** (CI, agents, docs) | **Frozen to maintenance.** Every plan states its status ([index](README.md#plans)); the journal is retired; the PR template and `/verify` are in English (#867). The e2e shards run in the pinned Playwright image (#886). A WebKit crash on `page.goto` (about 1% of runs) has its test-side trigger removed (#897); the upstream fix, Playwright 1.64, clears the npm 7-day cooldown on 2026-10-14. | W4 |

## Rules while the plan runs

CI and process work is frozen to maintenance, and there is no hosted instance: see
the plan's [ground rules](plan/PLAN_BEYOND_CI.md#context).

## Next 3 steps

1. **Playwright 1.64** on 2026-10-14, when it clears the npm cooldown: the lockfile, the
   image pin and the visual baselines, in one PR.
2. **Two bugs the W6 spike found:** the STV fiche fails on the default electorate (its
   seat count starts at 3, which three candidates cannot fill), and the Polis map's second
   axis takes its sign from the LAPACK build.
3. **The preprint** (D5), from the W2.6 piece. W3.5 (class mode) waits for the teacher
   outreach; W6's next steps wait for your decision.

## Waiting on the owner

- **The W6 decision:** static hosting with the engine in Pyodide, or the Fly container
  ([EXP-023](exploration/EXP-023-pyodide-web-worker-vs-fly-container.md) recommends
  Pyodide for a class, and lists what each path still needs).
- **The `e2e.yml` image pin** for Playwright 1.64, on 2026-10-14: the push token cannot
  push workflow files, so that two-line diff is yours.
- **#869's CI filter, still not applied.** The push token lacks GitHub's `workflow` scope,
  so the 4-line path-filter patch in #869's body is yours. Until then, a change to the
  registry or the bibliography alone does not run the backend check.
- **The venv's stale scripts** (`.venv/bin/lint-imports` still points at
  `/home/burbanit0/Vote-App/...`), which make fast-gate's layering check fail locally.
  Recreating the venv fixes it.
- **Outreach** (Phases 3–4): one social-choice researcher (W1.4), and one teacher for a
  projector demo (W3.5). The researcher's packet is ready
  ([`docs/research/expert-review-packet.md`](research/expert-review-packet.md)). Send it
  after the next release sync: its "report a content error" link opens an issue form, and
  GitHub reads issue forms from the default branch only.
- **The Zenodo upload** of the archived runs (W2.5).

## Open questions

- Why does founding not follow the stated threshold (OBS-045)? Rerun with every answer logged:
  all 14 founders it should have stopped founded, and none of 240 answers names the seat bar; those
  that say which threshold they mean cite the founding rule, also when it is worded without its
  percentage. Why the seat rule never enters the answer is still open.
- Expert review: are the 110 unsourced criteria cells right, and are W1.1's MJ
  "majority: conditional" and W1.2's two cell changes right?
- The tie lot's seed: #667's draws for a rule's tie use seed 0, so a given set of tied names
  always draws the same one. The per-voter draws vary from voter to voter (seeded with the
  voter's id), and only the nearest-option draws (#663, #665) also take the request's seed.
  Thread the request's seed into the others too?
- What remains of the 2026-10-09 tie decision has no issue yet: the ranked rules'
  tie-breaks on both engines (a parity-fixture regeneration), tallies that still break a tie
  by name, and approval (`docs/plan/vote-app/LISTING_ORDER_TIES.md`).
