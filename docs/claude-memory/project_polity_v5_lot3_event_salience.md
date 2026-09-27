---
name: project-polity-v5-lot3-event-salience
description: "v5 Lot 3 (§8 event_salience, awakening extension, deterministic reaction baseline) shipped in PR #144, merged to develop — two real bugs found and fixed during planning, not left as hypotheticals"
metadata:
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-15T18:14:40.708Z
---

v5 Lot 3 (`event_salience` + awakening extension + deterministic `reaction_to_event` baseline, §8) is
implemented and merged to `develop` 2026-08-15 (PR #144). Third lot of the v5 palier, following
Lot 1 (config/codebook, [[project_polity_v5_lot1_events_config]]) and Lot 2 (`shock.py` generators,
[[project_polity_v5_lot2_shock]]).

**What it does**: `Citizen.event_salience: float = 0.0` (appended last, decays like `street_pressure`
via new `accountability.update_event_salience`) — deliberately **never reset at election**, unlike
every other officeholder-scoped field, because a citizen's own residual awareness of a scandal has no
natural attachment to whichever officeholder happens to be sitting. `awakening_threshold` gained its
fourth term (event_salience lowers the threshold, folded into the existing shared clamp), **removing
Lot 1's placeholder `NotImplementedError` guard** — this is the guard v4/v5's whole "vacancy-only"
testing discipline had been routing around since Lot 2. `simple_rules.deterministic_reaction_to_event`
ships dt=8's §11.4 baseline: takes **no `Citizen` parameter at all** (stricter than
`deterministic_pressure_action`'s per-citizen `gap`) — a flat, population-wide delta applied
identically to everyone, which is also why `ReactionMotif.EVENT_PERSONALLY_IRRELEVANT` stays
structurally LLM-only. Wired into `_run_accountability_phase` as "step 0," journaling one
`reaction_to_event` event per citizen per firing generator (both motif=401/402 populated even on the
deterministic path — a deliberate divergence from `pressure_action`'s own "motif=None when no LLM ran"
precedent, since these motifs encode *which generator fired*, not a judgment).

**Two real bugs found and fixed during the planning pass itself** (this is the pattern worth
remembering — a "roadmap-level research" handoff can itself be wrong, verify against actual code
before trusting it):
1. A prior research draft placed the new step 0 *after* `representative_response` in
   `_run_accountability_phase`'s sequence. The roadmap's own text said "before step 1" — traced
   against the real code (no dependency either way) and corrected to match the roadmap literally.
2. **A same-tick ordering landmine**: `_run_exogenous_events` (finds the scandal's target) runs
   *before* any same-tick presidential election; `_run_accountability_phase` (where step 0 lives) runs
   *after*. Recomputing the target downstream would silently disagree with what `scandal_occurred`
   already journaled on any tick with both a scandal and an election. Fixed structurally: the target
   is captured once, at draw time, in a new `ExogenousEventsOutcome` frozen dataclass (replacing
   `_run_exogenous_events`'s old bare-`float` return) and threaded verbatim — never recomputed.

**Non-regression proof, load-bearing for the whole palier's design**: verified by test that
`event_salience`'s only channel into `écart(t)`/`L(t)` is the pre-existing `pressure_action`→
`street_pressure` path — a same-seed pair of runs (scandal firing vs. not, under `electoral_only`)
produces byte-identical `legitimacy_updated` payloads despite genuinely different consultation volume.
This is the empirical confirmation of v5's own top-level Judgment Call 3 (no fourth `écart(t)` term).

Zero behavior change at the shipped default; all 1314 tests pass (was 1297), byte-for-byte
reproducibility unmodified.

**How to apply**: v5 Lot 4 (dt=8 `reaction_to_event`, the LLM decision) needs its own planning pass —
not yet authorized. It's the first population-wide LLM decision type since `vote_cast` (dt=6/dt=10 are
both gated/consulted-subset only), so per the roadmap's own Risk 1, a batch-reliability spike is
required *before* any prompt-builder code is written — don't skip straight to schema design. See
[[project_polity_v5_lot2_shock]] for the sibling "verify claims against real output" discipline this
lot's two caught bugs reinforce again.
