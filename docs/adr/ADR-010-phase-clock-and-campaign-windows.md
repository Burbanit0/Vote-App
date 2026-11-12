# ADR-010: the phase clock and campaign windows

**Status**: Accepted — built in S4.4 (`plan-polity-build-order.md`)
**Date**: 2026-09-13
**Context**: Stage 4 of the polity build order ("a world that changes"). ADR-009 is reserved for
ordinary legislation (decision D3).

## Context

The simulation's calendar knew one thing about a tick: whether an election is held on it
(`InstitutionalClock.election_at`). Everything leading up to an election happened on the
election tick itself: candidacy, party nomination, campaign positioning and the vote. The
model's candidacy and nomination calls therefore came in one spike on the election tick.

Track E (`institutions.staggered_election`, off by default) spread a presidential election
over three ticks: declare two ticks before, nominate and position one tick before, vote on
the day. Its live check (`scripts/check_staggered_election_live_results.md`) left two bugs
with one root cause. On election day, the code decided "this cycle already staggered" by
looking for citizens holding `Role.CANDIDATE`. That is a proxy, and it fails both ways:

1. After a campaign interrupted by a rerun, a standing rupture candidate counted as proof
   that staggering had run. The party nominations never happened.
2. A campaign that produced no candidate counted as "did not stagger". Declaration and
   nomination re-ran on the election tick, the spike staggering exists to remove.

The build order asks for a phase that is a pure function of the tick, absorbing Track E,
with campaign windows of 4 ticks before presidential elections and 2 before legislative
ones.

## Decision

1. **A phase is a pure function of the tick.** `InstitutionalClock.phase(tick)` returns the
   election held that tick, whether a presidential and/or legislative campaign is running,
   and the ticks to each next election. A campaign is the `*_campaign_ticks` ticks before an
   election the run reaches. The tick-0 election has none, and the two kinds of campaign may
   overlap. Nothing journals the phase: any reader with the calendar recomputes it.
2. **The windows are configuration.** `institutions.presidential_campaign_ticks` (shipped 4)
   and `legislative_campaign_ticks` (shipped 2), non-negative.
3. **Track E is expressed through the presidential campaign.** A staggered election declares
   on the campaign's first tick and nominates and positions on its last. The campaign never
   reaches back to the previous presidential election's own tick; with a one-tick campaign,
   declaring and nominating share a tick. With no campaign, the election stays atomic.
   Reruns and snap elections stay atomic, as before.
4. **Whether a cycle staggered is recorded, not inferred.** The campaign's declared set stays
   in `TickState.staggered_declared_cids` (already checkpointed) until the election consumes
   it. The election is told `staggered=True` exactly when a set is waiting and no rerun
   interrupted it. Roles are no longer read for that purpose.

## Pre-registered facts

Checked before merging, in `test_polity_institutional_clock.py` and
`test_polity_run_simulation.py`:

- **Shipped calendar.** Presidential campaigns occupy ticks 12–15 before the election at 16,
  and legislative campaigns ticks 6–7 before the election at 8. After the last presidential
  election there is no presidential campaign.
- **Staggering on.** Candidacy decisions fall on each campaign's first tick, and nominations
  and positioning on its last. No presidential election tick after tick 0 carries a candidacy
  or nomination decision.
- **Both failure modes are gone.** An election that did not stagger nominates even with a
  rupture candidate standing. A staggered election whose campaign produced no candidate
  decides nothing again. A crash between nomination and vote resumes into the staggered
  election and produces the uninterrupted journal.
- **Control arm.** With `staggered_election` off, which is every recorded run, journals are
  unchanged: the golden references do not move.

Measured later, when a staggered run is made (needs the GPU): how far the election tick's
model calls fall, from the per-tick counts in `llm_calls.jsonl`.

## Consequences

- **Tick placement.** A staggered run's decisions move from ticks −2/−1 to the campaign's
  first and last ticks, which changes its RNG draw order. No recorded run staggered, so none
  is affected.
- **Available to later steps.** Campaign phases are available to anything that should behave
  differently during a campaign. The legislative campaign has no mechanics yet; S4.2
  (legislation) and S4.3 (dynamic citizens) are the natural consumers. What a campaign
  changes is their design question, not this ADR's.
