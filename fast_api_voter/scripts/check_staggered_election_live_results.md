# Staggered election verified live — Track E, 2026-09-11

## What was checked

`institutions.staggered_election` (default `false`) splits the fixed calendar's own
presidential election across three ticks — declare, nominate + position, vote —
instead of one. The fake-client tests in `test_polity_run_simulation.py` already
exercise the actual novel code (tick-loop dispatch, checkpoint round-trip, the
recall-interruption self-heal) at the Python level: `_consider_candidacies_llm`/
`_nominate_and_position_llm` call the exact same, already-verified
`decide_candidacies`/`decide_party_nominations`/`decide_campaign_positioning`
functions the atomic path always has, just from two new tick-loop positions. This
check's only job was confirming those calls still succeed against a REAL model
invoked from those new positions.

## Method

`check_staggered_election_live.py` — population 20, `president_term_years=1`
against the shipped `ticks_per_year=4` (a 4-tick term inside an 8-tick run), real
vLLM server, no fake client. Elections at ticks 0, 4, 8 — tick 0 has no runway to
stagger into (declare/nominate would need ticks -2/-1), ticks 4 and 8 each get a
real staggered window.

## Result: every check passed

```
candidacy_considered ticks: [0, 2, 6]
party_nomination_choice ticks: [0, 3, 7]
campaign_positioning ticks: [0, 3, 7]
vote_cast ticks: [0, 4, 8]
elected: [(0, 4), (4, 16), (8, 4)]
```

Tick 0: declaration, nomination, positioning and voting all land together, exactly
as the atomic path always has — confirmed no runway is used for the first
election. Ticks 4 and 8: declaration two ticks before, nomination+positioning one
tick before, voting on the calendar tick itself — the split is real, not a no-op.
A winner was elected at all three elections; the run did not deadlock or crash.

## A note on the `vote_cast` fallback warnings in the run's own stderr

The run logged several `vote_cast: exhausted every recovery attempt... falling
back to the deterministic sincere ranking` warnings, from `blank=1` responses that
also carried a non-empty `ranking` (a pre-existing §3.6.1 schema rule violation).
**This is unrelated to Track E** — the same failure mode this project's own
existing `cast_votes` fallback machinery already handles gracefully, on a decision
type and code path Track E does not touch at all (voting itself stays exactly
where it always was, on the calendar tick). Included here only so a future reader
of this run's own logs does not mistake it for something this change introduced.

## Disposition

**Mechanism confirmed working end-to-end against the real model.** Not wired into
`run_polity_flagship.py` this pass, deliberately: the plan's own risk note says to
do Track E and its owed re-baseline (`plan-distribution-positions-seeds.md`'s
`position_dist`/`ambition_threshold` work, Track D's territory) in the same pass,
never separately — turning this on for real flagship/production runs before that
re-baseline exists would ship a calendar shape nobody has validated at production
scale (p500, a full 30-year run). The config flag defaults to `false`, so every
existing run and test is completely unaffected; enabling it for real runs is a
deliberate, separate decision left for when Track D's own sweep happens.

## Addendum, 2026-09-13 — wired into the flagship runner, and one real bug found first

**Wired, still off by default.** `run_polity_flagship.py` gained
`--staggered-election` (opt-in). It is deliberately *not* force-enabled the way
`rupture_path_enabled`/`blank_vote_competitive`/`snap_election_on_recall` are:
turning it on changes the RNG draw order, so a run with it on is not comparable
to the p100 seed sweep or to Phase 7 Stage 3, both of which ran without it —
the same single-variable discipline as the version-pin decision in
`plan-distribution-positions-seeds.md` §4.2. This makes Track E *runnable* from
the flagship harness; it does not change what the next run measures.

**A real bug, found before enabling rather than after.** The staggered dispatch
in `run_polity_simulation.py` guards on `staggered_election and llm.enabled`, but
the `already_staggered` check at the election guarded only on
`staggered_election`. The two conditions disagreed, and the disagreement had
teeth: under the **deterministic** engine nothing staggers, yet
`rupture_path_enabled` (RNG-driven, LLM-independent, and force-enabled by this
very runner) can leave a standing rupture candidate holding `Role.CANDIDATE` on
election day — which satisfied `any(...)` by itself. `_declare_nominees` was then
skipped and that rupture candidate became the **entire** candidate field: an
election with no party nominees, silently, no error. Latent only because the flag
ships `false`; the first deterministic run with `--staggered-election` would have
produced quietly wrong elections. Fixed by adding the missing `llm.enabled` half,
with a regression test (`test_staggered_election_does_not_suppress_party_nominees_
on_the_deterministic_engine`) verified to fail without the fix and pass with it.

**Two sharp edges knowingly left unfixed** — both stem from the same root: the
election infers "staggering already ran this cycle" from citizen *roles*, which is
a proxy, not the fact itself (`staggered_declared_cids` is cleared at the
nomination tick, so it is already `None` by election day and cannot serve).
1. In LLM mode, if the declaration tick yields an empty declared set but a stale
   rupture candidate is standing, `already_staggered` is still true and party
   nominations are suppressed for that cycle.
2. Conversely, if staggering ran but produced no `Role.CANDIDATE` at all, the
   atomic fallback silently re-runs declaration+nomination *at the election tick*
   — reintroducing the very decision spike Track E exists to remove, paying for
   tick−2's work twice, and journaling nothing about it.

Fixing these properly means tracking "this cycle staggered" explicitly rather than
sniffing roles (e.g. not clearing `staggered_declared_cids` until the election
consumes it — it is already checkpointed, so no schema change). Not done here: it
changes behaviour that six existing tests pin, including byte-identical journal
equality, and Track E is off for the imminent p500 batch either way. **Do this
before any run that actually sets `--staggered-election`.**
