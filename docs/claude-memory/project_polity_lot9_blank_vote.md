---
name: project-polity-lot9-blank-vote
description: "§6bis.2 competitive blank voting shipped in PR #141, merged to develop — the one §13 v4 item deferred out of the v4 palier, now its own follow-up lot"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-15T13:22:40.895Z
---

§6bis.2 "vote blanc compétitif" is implemented and merged to `develop` 2026-08-15 (PR #141, "Lot 9" in the plan file `merry-hugging-hamming.md`). This was the one item the v4 palier's own top-level judgment call deliberately excluded from Lots 1-8 ("shares nothing with the rest of the palier ... defer to its own follow-up") — now done, closing out that deferral.

**What it does:** all six institutional config keys (`blank_vote_competitive`, `blank_invalidation_threshold`, `reelection_delay_ticks`, `reelection_max_attempts`, `barred_from_immediate_rerun`, plus the pre-existing `blank_vote_enabled`) shipped inert since v0/v4 and had zero effect until this lot. Now: a presidential election invalidates when `blank_share(t)` (fraction of ballots whose TOP preference is Blank) strictly exceeds the threshold; a rerun is scheduled with the fixed calendar **suspended** (not OR'd) until the cycle resolves; invalidated-election candidates are barred from the rerun (accumulating across repeated invalidations); beyond `reelection_max_attempts` a result is forced.

**Key architectural decision, worth remembering for similar future mechanics:** rerun state (`PendingRerun`: attempt, next_tick, barred_candidate_ids) is a **local run-scoped variable** threaded through the tick loop (same register as the existing `rupture_rng` local), deliberately NOT a `Citizen` field — unlike every other v4 officeholder-scoped mechanism (legitimacy_capital, street_pressure, petition state), an invalidated election has no officeholder to attach state to by construction. If a future mechanic needs cross-tick state with no natural office-holder, this is the precedent to reuse.

**A real bug caught during testing, not just reasoned about:** the additive `attempt`/`forced` keys on `elected`/`election_no_winner` were originally gated only on `config.institutions.blank_vote_competitive`, which meant turning the flag on changed journal bytes for EVERY election even when zero nominees ever existed (still added `attempt: 0, forced: 0`). Caught by an actual failing test (`test_blank_vote_competitive_enabled_but_never_triggered...`) against the true shipped default — the assumption "no citizen ever crosses ambition_threshold=0.7" from the plan turned out incomplete (nominees CAN exist even when elections never produce a winner). Fixed by additionally gating on `nominees` being non-empty. Lesson: even a well-reasoned "byte-for-byte no-op" claim in a plan should be verified by an actual failing/passing test at the real shipped config, not just asserted from reasoning — this project caught its own mistake exactly that way.

**Deliberately left open, named explicitly in the PR:** `_declare_nominees_llm` stays unfiltered by the barred set (extends the still-open Lot 2 term-limit/LLM-path asymmetry — never actually closed by Lot 6/7 as originally anticipated — rather than fixing it); legislative competitive-blank is out of scope entirely (doc says "l'élection" generically but every other v4 mechanic is presidency-only, and legislative invalidation has unaddressed blast radius — empty assembly, coalition formation).

**How to apply:** if extending §6bis.2 to the legislature, or closing the LLM-path barred/term-limit asymmetry, each needs its own planning pass — neither is scoped here. See [[project_polity_v4_lot8_llm_reliability]] for the sibling "verify claims against real output" discipline this lot's caught bug reinforces.
