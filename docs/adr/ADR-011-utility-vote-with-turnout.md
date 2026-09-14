# ADR-011: the utility vote, with turnout and an LLM audit sample

**Status**: Accepted — built in S4.1 (`plan-polity-build-order.md`). Weights ship at zero until
the calibration below.
**Date**: 2026-09-13
**Context**: decision D2 (2026-09-13) — a deterministic utility vote, with the LLM voting on an
audit sample.

## Context

Until S4.1 an LLM run asked the model to cast every ballot (`vote_cast`), and the deterministic
engine used `simple_rules.build_ranking`: the candidates within a voter's blank threshold, nearest
first, then blank. Three findings made the model vote the wrong tool for the population:

- **Cost.** At the election at tick 16 of the p500 batch's seed-1 run, `vote_cast` took 5,197 s of
  the tick's 5,598 s of model time, 1,297 s of it in retries, rejected answers and truncations
  (S1.1's per-tick attribution).
- **Little added.** The model mostly reproduces the sincere ballot: 23 of 24 correct at vLLM's shipped
  chunk size of 3 (`check_vllm_chunk_size_throughput_results.md`).
- **Nothing to react to.** Voters had nothing but distance to vote on, so the same field and the
  same electorate re-elected the same president (`observations.md` OBS-001). Decision D6 asked for
  a retrospective vote.

## Decision

1. **Every ballot is a utility ballot** (`simple_rules.utility_ballot`). A candidate's utility for a
   voter is:
   - minus the weighted distance, as today;
   - plus `vote.partisanship` if the candidate belongs to the voter's party;
   - plus `vote.approval` × the incumbent's record, if the candidate is the incumbent;
   - plus `vote.approval × vote.approval_party_carryover` × that record, for another candidate of
     the incumbent's party;
   - plus `vote.valence` × the candidate's valence.

   The record is 2 × legitimacy − 1, clamped to [−1, 1].

   Candidates whose utility reaches minus the voter's blank threshold rank above blank, highest
   first, ties to the lowest citizen id. That is `build_ranking` with utility in place of distance.
2. **The incumbent is the president the election judges**: the holder whose term ends at the
   election, or, for a rerun, the president its `PendingRerun` carries. That is the recalled
   president for a snap election, and the outgoing one through an invalidation cycle. No record is
   used while legitimacy is not tracked.
3. **Turnout is indifference abstention.** A voter stays home when their best option — a candidate,
   or the blank ballot worth minus their threshold — beats the next by less than
   `vote.turnout_cost`. The number who abstained is journaled on the election's outcome event.
4. **The model audits.** With `vote.mode: utility` (shipped), a run with a model asks `vote_cast`
   for a sample of voters: each is in with probability `vote.audit_fraction` (0.1), decided by a
   hash of seed, tick and citizen. The sample's ballots are journaled with `audit: 1` and never
   counted. `vote.mode: llm` keeps the model casting every ballot.
5. **Valence has no source yet.** The term exists; every valence is 0 until a mechanism (a scandal,
   say) sets one.

## Control arm and first acceptance

With every weight at zero a utility ballot is `build_ranking`'s ballot exactly: a Hypothesis
property over 400 generated electorates, including distance ties. The deterministic golden
reference does not move. Shipping the weights at zero therefore keeps today's sincere vote as the
control arm while changing who casts the ballots on LLM runs.

Timed on the p100 deterministic twin:

- **Per ballot:** a utility ballot costs 2.8 ms for 100 voters × 13 candidates, against 4.9 ms for
  `build_ranking`, which computes each distance twice.
- **Full run:** an 8-year p100 run takes 0.15 s.

## Pre-registered facts for the calibration

Measured on the p100 deterministic twin, seeds 1–10, 8 years, before any weight leaves zero. A
weight set is adopted only if all of these hold; each is also reported for the zero-weight arm.

1. **Retrospective voting.** An incumbent standing with a record below 0 is re-elected less often
   than one standing with a record of 0 or more.
2. **Turnout.** Mean turnout at presidential elections lies between 50% and 85%.
3. **Partisanship.** The share of voters whose first choice is their own party's candidate is
   higher than under the zero-weight arm, and below 90%.
4. **OBS-001, re-measured.** Runs with one president for all eight years are fewer than under the
   zero-weight arm.

**Measured on a live run:** the audit sample's agreement with the utility ballot's first choice,
read from its `vote_cast` events.

### Calibration result (2026-09-13)

`fast_api_voter/scripts/calibrate_utility_vote_results.md`, with the grid and selection
pre-registered in `plan-polity-build-order.md` §9. Fact 4 was restated before running: the term
limit of two rules out one-president runs for every arm, so it reads the share of elections won by
the previous winner.

**No setting meets all four facts, so the weights stay at 0.** None of the 36 settings qualifies.
What stops them:

- **Fact 1 cannot be judged at this size.** Ten seeds over 8 years give 0–7 incumbents standing per
  setting. Barred recalled presidents and term limits leave few. Where both groups stood,
  approval 0.05–0.1 mostly re-elects the negative-record group less often, but on one to five
  cases.
- **Fact 4 has no room.** The zero-weight arm's repeat-winner share is already 2.2% (2 of about 90
  pairs), so a setting must go lower on a handful of elections.
- **Turnout and partisanship pull against each other.** The band needs `turnout_cost` 0.02–0.04.
  `partisanship` 0.05 lifts own-party first choices from 71.7% to 86–92%, and 0.1 to 94–97%, past
  the 90% ceiling.

A better-powered protocol (more seeds or years) would be a new pre-registration, recorded as such.
It was not run.

## Consequences

- **LLM runs.** Journals change shape: `vote_cast` events are now the audit sample, so an election
  asks the model about a tenth of the voters. The p500 batch and every earlier LLM run voted through the
  model, so their vote shares are not comparable with runs after S4.1.
- **S2.1's concurrency sweep** measures `vote_cast` agreement, so it pins `vote.mode: llm`
  (`run_polity_flagship.py --vote-mode llm`).
- **Checkpoints.** A rerun's incumbent is written only when set, so an earlier checkpoint's format
  still reads. The new `vote` section enters `config_hash`, though, so a run started before S4.1
  resumes only under the code it started with.
