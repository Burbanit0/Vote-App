# PLAN.md — Step-up plan for Vote-App (playground + lab)

Self-contained execution plan. Six phases, one `feat/*` branch + one PR each.
Written to be executed by an agent with no prior context on this repo.

## Mission

Vote-App simulates voting methods and elector/candidate behavior. It is already
mechanically rich (29 rules, Monte-Carlo scorecard, sincerity/equilibrium/
robustness/valence modules, real-election backtest, electorate composer,
bilingual pedagogy layer). This plan closes the three remaining gaps:

1. **Intuitive** — nothing walks a newcomer through a *phenomenon* (only through
   the 5 UI moments). → Phase 1.
2. **Complete** — two pillars of the research literature are missing: VSE under
   behavioral voter mixes (Quinn), and candidate positioning dynamics
   (Downs/Hotelling). → Phases 2–3. Plus more real ballots (Phase 4) and the
   already-scoped multi-winner/lens work (Phase 5).
3. **Pretty** — no dedicated design pass since the instrument reshape; dark-mode
   CSS still targets a dead Bootstrap attribute. → Phase 6.

## Non-negotiable ground rules (read CLAUDE.md first — it is authoritative)

- **Workflow**: one `feat/*` branch per phase, **from `develop`**. PR against
  `develop`, merge `--no-ff`. Never commit features directly to `develop`.
- **Gates** (all must pass before a PR):
  - Frontend, run in `voter-app/`: `npx tsc --noEmit`, `npx vitest run`,
    `npm run lint` (0 errors), `npx prettier --config .prettierrc --write` on
    touched files, `npm run build`.
  - Backend, run in `fast_api_voter/` (only if touched): `python -m pytest`,
    `mypy api/` (strict, must stay clean).
- **Engine parity**: `voter-app/src/lib/playgroundVoting.ts` and
  `fast_api_voter/api/engine/utils/simulation_*_utils.py` are locked identical
  for 14 methods by `playgroundVoting.parity.test.ts`. **None of the phases
  below should modify rule logic.** If you must, re-run
  `python fast_api_voter/scripts/gen_engine_parity.py` and the parity test.
  Never hand-edit `engineParity.json`.
- **Architecture**: all playground state lives in
  `voter-app/src/components/playground/PlaygroundController.tsx` and flows
  through `usePlaygroundCtx`. Analytical logic = **pure lib in
  `voter-app/src/lib/` with unit tests + one thin component**. Follow that
  split for everything new. Heavy panels are `React.lazy` + collapsed by
  default (see `Collapsible.tsx`, `lazyWithPreload.ts`).
- **Don't denature the playground**: no new pages, no new drawers, no new
  top-level navigation. New capability = a lens, a module inside an existing
  moment, or a collapsed anchor in the Laboratoire page.
- **i18n**: namespace `playground`; `voter-app/src/i18n/locales/playground.fr.ts`
  is the source of truth AND the type; `playground.en.ts` must mirror it
  key-for-key (tsc enforces). **Tests run in English** — assert EN strings.
- **No new dependencies** unless a phase explicitly allows it (none do).
- Everything below is client-side; the backend stays untouched.

## Key existing files (reuse, don't reinvent)

| What | Where |
|---|---|
| Rule engine + types (`Rule`, `Pt`, `sampleVoters`…) | `voter-app/src/lib/playgroundVoting.ts` |
| Monte-Carlo scorecard (6 axes incl. welfare = 1−Bayesian regret) | `voter-app/src/lib/scorecard.ts` |
| Sincerity (compromise/burying bloc analysis) | `voter-app/src/lib/playgroundSincerity.ts` |
| Electorate composer (community mixtures) | `voter-app/src/lib/playgroundElectorate.ts` |
| Real-election backtest (Burlington 2009) | `voter-app/src/lib/realElections.ts` + `components/playground/RealElectionPanel.tsx` |
| Moment rail + guided walk (pattern for Phase 1) | `components/playground/MomentRail.tsx`, `GuidedFooter.tsx` |
| Flip animation centerpiece | `components/playground/FlipReveal.tsx` |
| Pedagogy registries (pattern: typed bilingual TS data) | `voter-app/src/lib/methodInfo.ts`, `scenarioInfo.ts` |
| Lens infrastructure (pattern for Phase 5) | grep `lens` under `components/playground/` |
| Moments (where new UI lands) | `components/playground/moments/*.tsx` |

---

## Phase 1 — Histoires: a scripted story player (branch `feat/stories`)

**Goal**: a newcomer can watch a voting-theory phenomenon unfold in the real
instrument, one beat at a time.

**Design**: a story is *data*, the player is thin, and it drives the SAME
playground (the GuidedFooter pattern applied to phenomena instead of moments).

- New pure lib `voter-app/src/lib/stories.ts`:
  - `interface StoryStep { id: string; state: Partial<PlaygroundState>; beatKey: string; focus?: MomentId }`
    — `state` is a patch applied to the playground context (candidates
    positions, rule, electorate preset, lens toggles, active moment);
    `beatKey` is an i18n key (one sentence per step); `focus` scrolls/activates
    a moment.
  - `interface Story { id: string; titleKey: string; steps: StoryStep[] }`
  - Registry of 6 stories:
    1. **The spoiler effect** — 2 candidates → add a third clone → plurality
       winner flips; switch to IRV/approval → flips back.
    2. **The center squeeze** — centrist eliminated first under IRV; end on the
       Burlington 2009 real-election panel.
    3. **A Condorcet cycle** — 3-community electorate producing A>B>C>A; show
       how minimax/schulze/ranked-pairs break the cycle differently.
    4. **The "vote utile" arms race** — sincerity module shows compromise
       temptation under plurality; switch rules until sincere is best response.
    5. **Majority vs welfare** — valence toggle makes the majority favorite and
       the welfare-optimal candidate diverge; compare scorecard axes.
    6. **One electorate, five winners** — same voters, cycle through 5 rules,
       FlipReveal each change.
- New thin component `components/playground/StoryPlayer.tsx`: overlay bar
  (title, beat sentence, step x/y, prev/next, quit). On step change, apply the
  state patch through existing context setters — **do not add a parallel state
  system**. Reuse `FlipReveal` when the winner changes.
- Entry points: a story picker card on `HomePage.tsx` and a button in the
  playground header. Story picker uses existing `Collapsible`/card primitives
  from `components/ui/`.
- i18n: all beats in `playground.fr.ts` + mirrored in `playground.en.ts`.

**Tests**: registry integrity (every story's `state` patch keys are valid
playground state keys — type-level where possible; every `beatKey`/`titleKey`
exists in both locales); player unit test (next/prev applies patches, quit
restores prior state). Assert EN strings.

**Done when**: 6 stories playable end-to-end, quitting a story restores the
user's previous sandbox state, all gates green.

## Phase 2 — Behavioral electorates + VSE (branch `feat/voter-behavior-vse`)

**Goal**: illustrate the central research result — how each method's welfare
degrades as voters turn strategic. This is Voter Satisfaction Efficiency
(Jameson Quinn, electionscience VSE work; Merrill 1984 before it).

- New pure lib `voter-app/src/lib/playgroundBehavior.ts`:
  - `interface BehaviorMix { honest: number; strategic: number; pollsAware: number }` (sums to 1).
  - `applyBehavior(voters, candidates, rule, mix, poll)` → ballots:
    - *honest*: sincere ranks/scores (current behavior, unchanged).
    - *strategic*: naive compromise — rank the preferred of the top-two poll
      leaders first, the other last (reuse the taxonomy already in
      `playgroundSincerity.ts`; extract shared helpers rather than duplicating).
    - *pollsAware*: one poll-feedback iteration — vote strategically against
      the winner of a first sincere round.
  - `computeVSE(rule, mix, rerolls)` — Monte-Carlo over fresh electorates
    (copy the re-roll pattern from `scorecard.ts`, including Wilson/band
    conventions): VSE = (E[u(winner)] − E[u(random)]) / (E[u(best)] − E[u(random)]).
  - **This layer sits strictly above `ruleWinnerFromRanks` — do not touch rule
    logic; parity fixtures must not change.**
- UI, inside the existing **Stratégie moment** (`moments/StrategyMoment.tsx`):
  - a behavior-mix control (3 sliders or a single 2-thumb slider; keep it to
    one compact block, collapsed advanced options if needed);
  - one chart: VSE per rule as strategic share sweeps 0 → 100% (line per rule,
    confidence band). Follow the existing SVG-native vs Recharts conventions
    (see the `voter-ui` skill if available; otherwise mimic neighboring charts).
- The scorecard's welfare axis gains an optional "under current behavior mix"
  readout (keep the honest baseline visible — never replace it).
- Pedagogy: one `methodInfo.ts`-style registry entry / InfoPopover citing
  Quinn (VSE), Merrill (1984), Green-Armytage–Tideman–Graham-Squire (2016).

**Tests**: pure-lib unit tests — mix {honest:1} reproduces current sincere
winners exactly (regression guard); a known 3-candidate center-squeeze profile
shows plurality VSE dropping faster than approval/STAR; determinism per seed.

**Done when**: sweep chart renders with bands, honest baseline unchanged
everywhere else, parity test untouched and green, gates green.

## Phase 3 — Candidate positioning dynamics (branch `feat/candidate-dynamics`)

**Goal**: the other half of "simulate people behavior" — candidates move.
Downs/Hotelling: equilibrium positions differ per rule (plurality disperses,
Condorcet-consistent rules pull toward the median voter, IRV squeezes the
center out).

- New pure lib `voter-app/src/lib/candidateDynamics.ts`:
  - `bestResponseStep(candidates, voters, rule, focalIdx)` — sample K candidate
    positions in a radius around the focal candidate (grid or ring; keep it
    simple and deterministic), return the position maximizing that candidate's
    outcome (win first, then vote share/score as tiebreak) with all others fixed.
  - `iterateDynamics(candidates, voters, rule, steps)` — round-robin best
    responses; return the full trajectory (array of position frames) so the UI
    can animate; stop early at a fixed point.
  - `entryIncentive(candidates, voters, rule, probe)` — would a new entrant at
    `probe` win, or change the winner (spoiler)? Returns enough to paint an
    "entry map" overlay (win / spoil / no-effect per probed cell).
- UI, inside the existing **Campagne moment**: a play/pause/reset control that
  animates candidate dots along the trajectory on the existing map canvas
  (`LeaderCanvas`), plus an optional entry-incentive lens overlay following the
  existing lens infrastructure. Respect the form-lock performance invariant
  (see `voter-ui` skill / neighboring components): animation must not re-run
  the Monte-Carlo modules on every frame — compute the trajectory once.
- Pedagogy: InfoPopover citing Downs 1957 (median voter), Hotelling 1929,
  Myerson–Weber 1993.

**Tests**: with a symmetric 1-community electorate and 2 candidates under
plurality, both converge toward the median (Hotelling); under a 3-candidate
IRV profile a known center-squeeze persists; `iterateDynamics` is
deterministic and terminates.

**Done when**: play button animates convergence, per-rule equilibria visibly
differ on the same electorate, no interaction jank, gates green.

## Phase 4 — More real elections (branch `feat/real-elections-2`)

**Goal**: two more grounded datasets alongside Burlington 2009, reusing
`realElections.ts` + `RealElectionPanel.tsx` unchanged in structure.

1. **Alaska 2022 special (US House, August)** — the famous real-world IRV
   Condorcet failure (Begich was the Condorcet winner; Peltola won). Public
   cast-vote-record aggregations exist; encode the aggregated ranking profile
   (a few dozen distinct ballot types with counts) exactly like the Burlington
   entry. Verify: IRV → Peltola, Condorcet → Begich, plurality → Palin.
2. **France, "Voter Autrement" 2017 (approval voting experiment)** — encode the
   published approval profile; show approval winner vs the official two-round
   result. If ballot-level data is too coarse, encode the published aggregate
   approval rates with a clearly-labeled caveat in the panel copy.
- Follow the existing data shape and validation tests in `realElections.test.ts`;
  add the same sanity assertions (totals, known winners per rule).
- i18n: panel copy for both elections in FR + EN.

**Done when**: both elections selectable in the panel, known historical
outcomes reproduced by the corresponding rules, gates green.

## Phase 5 — Lens completion + multi-winner MES/JR (branch `feat/lenses-2`)

**Goal**: finish the already-scoped lens roadmap (manipulation + criteria
lenses) and add the one modern multi-winner result the app lacks: **Method of
Equal Shares + Justified Representation** for the Assemblée (parliament) mode.

- Follow the lens PR1 pattern exactly (grep the lens infrastructure added with
  Ranked Pairs / random ballot; commit 2ad24c9): new lenses are toggles on the
  central map, not new panels.
  - *Manipulation lens*: color each map cell by whether the sincere winner
    there is manipulable (reuse `playgroundSincerity.ts` verdicts).
  - *Criteria lens*: highlight where a selected criterion (from
    `playgroundCriteria.ts`) fails for the current rule.
- MES/JR (Assemblée mode only): pure lib `voter-app/src/lib/multiWinner.ts`
  implementing Method of Equal Shares over the composed electorate's approval
  ballots, plus a JR/EJR checker for any committee. Surface as one additional
  parliament allocation option + a "representation" readout (JR satisfied?).
  - MES is client-only (Tier-B style: no backend twin, **excluded from the
    parity fixture set** — do not add it to comparison surfaces that assert
    backend parity).
  - Cite Peters–Skowron (MES), Aziz et al. (JR/EJR) in an InfoPopover.

**Tests**: MES on the canonical small examples from the literature (e.g. the
Peters–Skowron illustrative instances); JR checker positive + negative cases;
lens toggles render without recomputing unrelated modules.

**Done when**: both lenses toggleable, MES selectable in Assemblée mode with a
JR readout, parity untouched, gates green.

## Phase 6 — The pretty pass (branch `feat/design-pass`)

**Goal**: one dedicated visual PR. No behavior changes — snapshot-level risk only.

1. **Dark mode**: `voter-app/src/styles/tailwind.css` still has a
   `[data-bs-theme='dark']` block — Bootstrap is gone. Either wire real dark
   mode (Tailwind `dark:` variant + a toggle, updating shadcn token values) or
   delete the dead block and ship light-only deliberately. Decide by effort:
   if the shadcn tokens already have dark values, wire it; otherwise delete.
2. **Chart consistency sweep**: one palette + one typography scale across all
   playground/lab charts (axis label sizes, band opacities, winner-color
   semantics identical everywhere). If a `dataviz` skill is available to the
   executing agent, load it before touching chart colors.
3. **Motion**: unify winner-flip and scorecard-band transitions on the
   `FlipReveal` timing constants; add number-transition on scorecard values.
   Keep every animation interruptible and under ~300ms except FlipReveal.
4. **Homepage hero**: the live map as the hero — render the actual
   `LeaderCanvas` with a slow autonomous demo loop (rule cycling) instead of
   any static illustration. Reuse Phase 1's story-step applier if it helps.
5. Run the full gate suite + a manual pass of every moment in FR and EN, light
   (and dark if shipped).

**Done when**: no visual regressions in existing tests, consistent charts,
hero live, gates green.

---

## Execution order

1 → 2 → 3 as the spine (intuitive first — it multiplies the value of later
phases — then the two research pillars). 4 and 5 are independent of the spine
and of each other; interleave freely. 6 goes **last** so it polishes the final
surface once.

Per-phase definition of done (applies to all): gates green, FR+EN locales in
sync, tests assert EN strings, no new dependencies, parity fixtures
byte-identical unless a rule was deliberately changed (none should be), PR
against `develop` with a description linking back to this plan's phase.
